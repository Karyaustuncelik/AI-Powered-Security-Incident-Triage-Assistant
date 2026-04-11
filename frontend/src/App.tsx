import { useEffect, useState } from 'react'
import { generateExplanation } from './api/explain'
import { fetchFilterOptions } from './api/filters'
import { fetchIncidentDetail, fetchIncidents } from './api/incidents'
import { saveIncidentReview } from './api/review'
import { fetchStats } from './api/stats'
import { ActiveFilterChips } from './components/ActiveFilterChips'
import { DistributionCard } from './components/DistributionCard'
import { FilterBar } from './components/FilterBar'
import { IncidentDetailPanel } from './components/IncidentDetailPanel'
import { IncidentQueueTable } from './components/IncidentQueueTable'
import { RecentQueueCard } from './components/RecentQueueCard'
import { SummaryCards } from './components/SummaryCards'
import type {
  FilterOptionsResponse,
  IncidentDetail,
  IncidentFilters,
  IncidentListItem,
  StatsResponse,
} from './types/incident'
import { formatLabel, getTopBucket } from './utils/format'
import './App.css'

function App() {
  const [incidents, setIncidents] = useState<IncidentListItem[]>([])
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null)
  const [selectedIncident, setSelectedIncident] = useState<IncidentDetail | null>(null)
  const [filterOptions, setFilterOptions] = useState<FilterOptionsResponse | null>(null)
  const [filters, setFilters] = useState<IncidentFilters>({
    severity: '',
    priority: '',
    review_status: '',
    event_type: '',
    actor_user: '',
    affected_entity: '',
    search: '',
    start_time: '',
    end_time: '',
  })
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(true)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)
  const [isGeneratingExplanation, setIsGeneratingExplanation] = useState(false)
  const [isSavingReview, setIsSavingReview] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [refreshVersion, setRefreshVersion] = useState(0)

  useEffect(() => {
    let isCancelled = false

    async function loadFilterOptions() {
      try {
        const options = await fetchFilterOptions()
        if (!isCancelled) {
          setFilterOptions(options)
        }
      } catch (error) {
        if (!isCancelled) {
          setErrorMessage(
            error instanceof Error
              ? error.message
              : 'Filtre seçenekleri alınırken bilinmeyen bir hata oluştu.',
          )
        }
      }
    }

    void loadFilterOptions()

    return () => {
      isCancelled = true
    }
  }, [])

  useEffect(() => {
    let isCancelled = false

    async function loadDashboard() {
      try {
        setIsLoadingDashboard(true)
        setErrorMessage(null)

        const [incidentItems, statsResponse] = await Promise.all([
          fetchIncidents(filters),
          fetchStats(filters),
        ])

        if (isCancelled) {
          return
        }

        setIncidents(incidentItems)
        setStats(statsResponse)
        setSelectedIncidentId((currentSelectedIncidentId) => {
          if (incidentItems.length === 0) {
            return null
          }

          const selectedStillExists = incidentItems.some(
            (incident) => incident.incident_id === currentSelectedIncidentId,
          )

          return selectedStillExists
            ? currentSelectedIncidentId
            : incidentItems[0].incident_id
        })
      } catch (error) {
        if (!isCancelled) {
          setErrorMessage(
            error instanceof Error
              ? error.message
              : 'Dashboard verisi alınırken bilinmeyen bir hata oluştu.',
          )
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingDashboard(false)
        }
      }
    }

    void loadDashboard()

    return () => {
      isCancelled = true
    }
  }, [filters, refreshVersion])

  useEffect(() => {
    let isCancelled = false

    async function loadIncidentDetail() {
      if (!selectedIncidentId) {
        setSelectedIncident(null)
        return
      }

      try {
        setIsLoadingDetail(true)
        const detail = await fetchIncidentDetail(selectedIncidentId)

        if (!isCancelled) {
          setSelectedIncident(detail)
        }
      } catch (error) {
        if (!isCancelled) {
          setErrorMessage(
            error instanceof Error
              ? error.message
              : 'Incident detayı alınırken bilinmeyen bir hata oluştu.',
          )
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingDetail(false)
        }
      }
    }

    void loadIncidentDetail()

    return () => {
      isCancelled = true
    }
  }, [selectedIncidentId])

  const topCategory = getTopBucket(stats?.category_distribution ?? [])
  const immediateAttentionCount =
    stats?.priority_distribution.find((item) => item.label === 'immediate_attention')?.count ?? 0

  const summaryCards = [
    {
      label: 'Total Incidents',
      value: String(stats?.total_incidents ?? 0),
      note: 'Curated local dataset',
    },
    {
      label: 'High / Critical',
      value: String(stats?.high_or_critical_count ?? 0),
      note: 'Needs analyst focus',
    },
    {
      label: 'Immediate Attention',
      value: String(immediateAttentionCount),
      note: 'Escalated by triage engine',
    },
    {
      label: 'Top Category',
      value: topCategory ? formatLabel(topCategory.label) : 'N/A',
      note: 'Most frequent incident family',
    },
  ]

  function updateFilter(name: keyof IncidentFilters, value: string) {
    setFilters((currentFilters) => ({
      ...currentFilters,
      [name]: value,
    }))
  }

  function resetFilters() {
    setFilters({
      severity: '',
      priority: '',
      review_status: '',
      event_type: '',
      actor_user: '',
      affected_entity: '',
      search: '',
      start_time: '',
      end_time: '',
    })
  }

  async function handleGenerateExplanation() {
    if (!selectedIncidentId || !selectedIncident) {
      return
    }

    try {
      setIsGeneratingExplanation(true)
      const explanation = await generateExplanation(selectedIncidentId)
      setSelectedIncident({
        ...selectedIncident,
        llm_explanation: explanation,
      })
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : 'Explanation üretilirken bilinmeyen bir hata oluştu.',
      )
    } finally {
      setIsGeneratingExplanation(false)
    }
  }

  async function handleSaveReview(payload: {
    review_status: string
    assigned_analyst: string
    review_notes: string
  }) {
    if (!selectedIncidentId || !selectedIncident) {
      return
    }

    try {
      setIsSavingReview(true)
      const review = await saveIncidentReview(selectedIncidentId, payload)
      setSelectedIncident({
        ...selectedIncident,
        review,
      })
      setRefreshVersion((current) => current + 1)
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : 'Review kaydedilirken bilinmeyen bir hata oluştu.',
      )
    } finally {
      setIsSavingReview(false)
    }
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">AI-Powered Security Incident Triage Assistant</p>
        <h1>Security incidents, prioritized and explained.</h1>
        <p className="hero-copy">
          This local-first dashboard correlates suspicious activity, assigns rule-based risk,
          and produces analyst-ready explanations for each incident.
        </p>
      </section>

      {errorMessage ? (
        <section className="error-banner">
          <strong>Backend connection issue:</strong> {errorMessage}
        </section>
      ) : null}

      <SummaryCards cards={summaryCards} />

      <FilterBar
        filterOptions={filterOptions}
        filters={filters}
        onFilterChange={updateFilter}
        onReset={resetFilters}
      />

      <ActiveFilterChips filters={filters} />

      <section className="insights-grid">
        <DistributionCard
          buckets={stats?.category_distribution ?? []}
          isLoading={isLoadingDashboard}
          title="Category Distribution"
        />
        <DistributionCard
          buckets={stats?.priority_distribution ?? []}
          isLoading={isLoadingDashboard}
          title="Priority Distribution"
        />
        <DistributionCard
          buckets={stats?.review_status_distribution ?? []}
          isLoading={isLoadingDashboard}
          title="Review Status Distribution"
        />
        <RecentQueueCard
          incidents={stats?.recent_incidents ?? []}
          onSelect={setSelectedIncidentId}
        />
      </section>

      <section className="workspace">
        <IncidentQueueTable
          incidents={incidents}
          isLoading={isLoadingDashboard}
          onSelect={setSelectedIncidentId}
          selectedIncidentId={selectedIncidentId}
        />
        <IncidentDetailPanel
          incident={selectedIncident}
          isGeneratingExplanation={isGeneratingExplanation}
          isLoading={isLoadingDetail}
          isSavingReview={isSavingReview}
          onGenerateExplanation={handleGenerateExplanation}
          onSaveReview={handleSaveReview}
        />
      </section>
    </main>
  )
}

export default App
