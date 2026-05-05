import { useEffect, useState } from 'react'
import { generateExplanation } from './api/explain'
import { fetchFilterOptions } from './api/filters'
import { chatAboutIncident, fetchIncidentDetail, fetchIncidents } from './api/incidents'
import { saveIncidentReview } from './api/review'
import { fetchStats } from './api/stats'
import {
  chatAboutUploadedIncident,
  fetchUploadedFilterOptions,
  fetchUploadedIncidentDetail,
  fetchUploadedIncidents,
  fetchUploadedStats,
  uploadLogs,
} from './api/uploads'
import { ActiveFilterChips } from './components/ActiveFilterChips'
import { DistributionCard } from './components/DistributionCard'
import { FilterBar } from './components/FilterBar'
import { IncidentCopilotPanel } from './components/IncidentCopilotPanel'
import { IncidentDetailPanel } from './components/IncidentDetailPanel'
import { IncidentQueueTable } from './components/IncidentQueueTable'
import { RecentQueueCard } from './components/RecentQueueCard'
import { SummaryCards } from './components/SummaryCards'
import { UploadPanel } from './components/UploadPanel'
import { startPentestSession, submitPentestStep, generatePentestReport } from './api/pentest'
import { AttackMap } from './components/nebula/AttackMap'
import { KillChainBuilder } from './components/nebula/KillChainBuilder'
import { LandingPage } from './components/nebula/LandingPage'
import { NavBar, type Route } from './components/nebula/NavBar'
import { NebulaCopilot } from './components/nebula/NebulaCopilot'
import { Starfield } from './components/nebula/Starfield'
import { ThreatIntel } from './components/nebula/ThreatIntel'
import { PentestWorkspace } from './components/PentestWorkspace'
import type {
  FilterOptionsResponse,
  IncidentCopilotMessage,
  IncidentDetail,
  IncidentFilters,
  IncidentListItem,
  StatsResponse,
  UploadSession,
} from './types/incident'
import { formatLabel, getTopBucket } from './utils/format'

import './components/nebula/navbar.css'
import './components/nebula/landing.css'
import './components/nebula/nebula-copilot.css'
import './components/nebula/attack-map.css'
import './components/nebula/kill-chain.css'
import './components/nebula/threat-intel.css'
import './App.css'

const EMPTY_FILTERS: IncidentFilters = {
  severity: '',
  priority: '',
  review_status: '',
  event_type: '',
  actor_user: '',
  affected_entity: '',
  search: '',
  start_time: '',
  end_time: '',
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  const chunkSize = 0x8000
  let binary = ''
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize)
    binary += String.fromCharCode(...chunk)
  }
  return btoa(binary)
}

// Simple hash-based router
function useHashRoute(): [Route, (r: Route) => void] {
  const getRoute = (): Route => {
    const hash = window.location.hash.replace('#', '') || '/'
    const valid: Route[] = ['/', '/dashboard', '/sirius', '/attack-map', '/kill-chain', '/threat-intel', '/pentest']
    return valid.includes(hash as Route) ? (hash as Route) : '/'
  }

  const [route, setRoute] = useState<Route>(getRoute)

  useEffect(() => {
    const onHash = () => setRoute(getRoute())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const navigate = (r: Route) => {
    window.location.hash = r
    setRoute(r)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return [route, navigate]
}

function App() {
  const [route, navigate] = useHashRoute()
  const [activeUploadSession, setActiveUploadSession] = useState<UploadSession | null>(null)
  const [incidents, setIncidents] = useState<IncidentListItem[]>([])
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null)
  const [selectedIncident, setSelectedIncident] = useState<IncidentDetail | null>(null)
  const [filterOptions, setFilterOptions] = useState<FilterOptionsResponse | null>(null)
  const [filters, setFilters] = useState<IncidentFilters>({ ...EMPTY_FILTERS })
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(true)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)
  const [isUploadingLog, setIsUploadingLog] = useState(false)
  const [isGeneratingExplanation, setIsGeneratingExplanation] = useState(false)
  const [isSendingCopilot, setIsSendingCopilot] = useState(false)
  const [isSavingReview, setIsSavingReview] = useState(false)
  const [copilotMessages, setCopilotMessages] = useState<IncidentCopilotMessage[]>([])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [refreshVersion, setRefreshVersion] = useState(0)

  // Only load dashboard data when on dashboard route
  const isDashboardActive = route === '/dashboard'

  useEffect(() => {
    if (!isDashboardActive) return
    let isCancelled = false

    async function loadFilterOptions() {
      try {
        const options = activeUploadSession
          ? await fetchUploadedFilterOptions(activeUploadSession.upload_id)
          : await fetchFilterOptions()
        if (!isCancelled) setFilterOptions(options)
      } catch (error) {
        if (!isCancelled) {
          setErrorMessage(
            error instanceof Error ? error.message : 'Filtre seçenekleri alınırken hata oluştu.',
          )
        }
      }
    }

    void loadFilterOptions()
    return () => { isCancelled = true }
  }, [activeUploadSession, isDashboardActive])

  useEffect(() => {
    if (!isDashboardActive) return
    let isCancelled = false

    async function loadDashboard() {
      try {
        setIsLoadingDashboard(true)
        setErrorMessage(null)

        const [incidentItems, statsResponse] = activeUploadSession
          ? await Promise.all([
              fetchUploadedIncidents(activeUploadSession.upload_id, filters),
              fetchUploadedStats(activeUploadSession.upload_id, filters),
            ])
          : await Promise.all([fetchIncidents(filters), fetchStats(filters)])

        if (isCancelled) return
        setIncidents(incidentItems)
        setStats(statsResponse)
        setSelectedIncidentId((currentSelectedIncidentId) => {
          if (incidentItems.length === 0) return null
          const selectedStillExists = incidentItems.some(
            (incident) => incident.incident_id === currentSelectedIncidentId,
          )
          return selectedStillExists ? currentSelectedIncidentId : incidentItems[0].incident_id
        })
      } catch (error) {
        if (!isCancelled) {
          setErrorMessage(
            error instanceof Error ? error.message : 'Dashboard verisi alınırken hata oluştu.',
          )
        }
      } finally {
        if (!isCancelled) setIsLoadingDashboard(false)
      }
    }

    void loadDashboard()
    return () => { isCancelled = true }
  }, [activeUploadSession, filters, refreshVersion, isDashboardActive])

  useEffect(() => {
    if (!isDashboardActive) return
    let isCancelled = false

    async function loadIncidentDetail() {
      if (!selectedIncidentId) { setSelectedIncident(null); return }
      try {
        setIsLoadingDetail(true)
        const detail = activeUploadSession
          ? await fetchUploadedIncidentDetail(activeUploadSession.upload_id, selectedIncidentId)
          : await fetchIncidentDetail(selectedIncidentId)
        if (!isCancelled) setSelectedIncident(detail)
      } catch (error) {
        if (!isCancelled) {
          setErrorMessage(
            error instanceof Error ? error.message : 'Incident detayı alınırken hata oluştu.',
          )
        }
      } finally {
        if (!isCancelled) setIsLoadingDetail(false)
      }
    }

    void loadIncidentDetail()
    return () => { isCancelled = true }
  }, [activeUploadSession, selectedIncidentId, isDashboardActive])

  useEffect(() => {
    setCopilotMessages([])
  }, [activeUploadSession, selectedIncidentId])

  const topCategory = getTopBucket(stats?.category_distribution ?? [])
  const immediateAttentionCount =
    stats?.priority_distribution.find((item) => item.label === 'immediate_attention')?.count ?? 0
  const isUploadMode = activeUploadSession !== null
  const dataSourceLabel = activeUploadSession
    ? `Upload: ${activeUploadSession.filename}`
    : 'Curated dataset'

  const summaryCards = [
    { label: 'Total Incidents', value: String(stats?.total_incidents ?? 0), note: dataSourceLabel },
    {
      label: 'High / Critical',
      value: String(stats?.high_or_critical_count ?? 0),
      note: activeUploadSession ? `${activeUploadSession.raw_event_count} raw events` : 'Needs analyst focus',
    },
    {
      label: 'Immediate Attention',
      value: String(immediateAttentionCount),
      note: activeUploadSession ? `${activeUploadSession.normalized_event_count} normalized` : 'Escalated by triage',
    },
    {
      label: 'Top Category',
      value: topCategory ? formatLabel(topCategory.label) : 'N/A',
      note: activeUploadSession ? `${activeUploadSession.incident_count} correlated` : 'Most frequent family',
    },
  ]

  function updateFilter(name: keyof IncidentFilters, value: string) {
    setFilters((currentFilters) => ({ ...currentFilters, [name]: value }))
  }

  function resetFilters() {
    setFilters({ ...EMPTY_FILTERS })
  }

  async function handleUploadLog(file: File) {
    try {
      setIsUploadingLog(true)
      setErrorMessage(null)
      const session = await uploadLogs({
        filename: file.name,
        content_base64: arrayBufferToBase64(await file.arrayBuffer()),
      })
      setActiveUploadSession(session)
      setFilters({ ...EMPTY_FILTERS })
      setSelectedIncidentId(null)
      setSelectedIncident(null)
      setRefreshVersion((c) => c + 1)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Log yüklenirken hata oluştu.')
    } finally {
      setIsUploadingLog(false)
    }
  }

  function handleReturnToDemoDataset() {
    setActiveUploadSession(null)
    setFilters({ ...EMPTY_FILTERS })
    setSelectedIncidentId(null)
    setSelectedIncident(null)
    setErrorMessage(null)
    setRefreshVersion((c) => c + 1)
  }

  async function handleGenerateExplanation() {
    if (!selectedIncidentId || !selectedIncident || isUploadMode) return
    try {
      setIsGeneratingExplanation(true)
      const explanation = await generateExplanation(selectedIncidentId)
      setSelectedIncident({ ...selectedIncident, llm_explanation: explanation })
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Explanation üretilirken hata oluştu.')
    } finally {
      setIsGeneratingExplanation(false)
    }
  }

  async function handleSendCopilotQuestion(question: string) {
    if (!selectedIncidentId) return
    const userMessage: IncidentCopilotMessage = { role: 'user', content: question }
    try {
      setIsSendingCopilot(true)
      setErrorMessage(null)
      setCopilotMessages((current) => [...current, userMessage])
      const response = activeUploadSession
        ? await chatAboutUploadedIncident(activeUploadSession.upload_id, selectedIncidentId, { question, history: copilotMessages })
        : await chatAboutIncident(selectedIncidentId, { question, history: copilotMessages })
      setCopilotMessages((current) => [...current, response.answer])
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Copilot yanıtı alınamadı.')
      setCopilotMessages((current) => [
        ...current,
        { role: 'assistant', content: 'Copilot yanıtı alınamadı. Backend bağlantısını kontrol edin.' },
      ])
    } finally {
      setIsSendingCopilot(false)
    }
  }

  async function handleSaveReview(payload: {
    review_status: string
    assigned_analyst: string
    review_notes: string
  }) {
    if (!selectedIncidentId || !selectedIncident) return
    try {
      setIsSavingReview(true)
      const review = await saveIncidentReview(selectedIncidentId, payload)
      setSelectedIncident({ ...selectedIncident, review })
      setRefreshVersion((c) => c + 1)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Review kaydedilirken hata oluştu.')
    } finally {
      setIsSavingReview(false)
    }
  }

  // Render pages
  const renderPage = () => {
    switch (route) {
      case '/':
        return <LandingPage onNavigate={navigate} />

      case '/dashboard':
        return (
          <div className="dashboard-page page-enter">
            <section className="hero">
              <p className="eyebrow">Security Dashboard</p>
              <h1>
                Incidents, <span className="text-gradient">analyzed.</span>
              </h1>
              <p className="hero-copy">
                Rule-based triage engine correlates suspicious activity, assigns risk scores,
                and produces analyst-ready explanations in real-time.
              </p>
            </section>

            {errorMessage && (
              <section className="error-banner">
                <strong>Connection issue:</strong> {errorMessage}
              </section>
            )}

            <UploadPanel
              activeSession={activeUploadSession}
              isUploading={isUploadingLog}
              onResetToDemo={handleReturnToDemoDataset}
              onUpload={handleUploadLog}
            />

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
                title="Review Status"
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
              <div className="detail-column">
                <IncidentDetailPanel
                  incident={selectedIncident}
                  isGeneratingExplanation={isGeneratingExplanation}
                  isLoading={isLoadingDetail}
                  isSavingReview={isSavingReview}
                  onGenerateExplanation={handleGenerateExplanation}
                  onSaveReview={handleSaveReview}
                  showExplanationSection={!isUploadMode}
                />
                <IncidentCopilotPanel
                  incident={selectedIncident}
                  isSending={isSendingCopilot}
                  messages={copilotMessages}
                  modeLabel={isUploadMode ? 'Uploaded Evidence' : 'Curated Dataset'}
                  onSend={handleSendCopilotQuestion}
                />
              </div>
            </section>
          </div>
        )

      case '/sirius':
        return (
          <div className="dashboard-page page-enter">
            <section className="hero">
              <p className="eyebrow">SIRIUS AI Copilot</p>
              <h1>
                Red Team <span className="text-gradient">Intelligence.</span>
              </h1>
              <p className="hero-copy">
                Your AI-powered offensive security companion. 5 specialized modes for
                recon, exploitation, attack chains, reporting, and general advisory.
              </p>
            </section>
            <NebulaCopilot />
          </div>
        )

      case '/pentest':
        return (
          <div className="dashboard-page page-enter">
            <section className="hero">
              <p className="eyebrow">SIRIUS AI · Pentest Workspace</p>
              <h1>
                Collaborative <span className="text-gradient">Penetration Testing.</span>
              </h1>
              <p className="hero-copy">
                Describe your target and observations. SIRIUS AI generates a step-by-step
                test plan, analyses your outputs, and produces a professional LaTeX report.
              </p>
            </section>
            <PentestWorkspace
              onStartSession={(req) => startPentestSession(req)}
              onSubmitStep={(id, idx, out) => submitPentestStep(id, idx, out)}
              onGenerateReport={(id) => generatePentestReport(id)}
            />
          </div>
        )

      case '/attack-map':
        return (
          <div className="dashboard-page page-enter">
            <section className="hero">
              <p className="eyebrow">Attack Visualization</p>
              <h1>
                Global Attack <span className="text-gradient">Map.</span>
              </h1>
              <p className="hero-copy">
                Real-time visualization of attack vectors across the globe. Track threat origins,
                correlate geolocation data, and identify threat patterns.
              </p>
            </section>
            <AttackMap />
          </div>
        )

      case '/kill-chain':
        return (
          <div className="dashboard-page page-enter">
            <section className="hero">
              <p className="eyebrow">Attack Planning</p>
              <h1>
                Kill Chain <span className="text-gradient">Builder.</span>
              </h1>
              <p className="hero-copy">
                Construct MITRE ATT&CK-aligned kill chains visually. Select tactics,
                add techniques, and build comprehensive attack plans.
              </p>
            </section>
            <KillChainBuilder />
          </div>
        )

      case '/threat-intel':
        return (
          <div className="dashboard-page page-enter">
            <section className="hero">
              <p className="eyebrow">Intelligence Feed</p>
              <h1>
                Threat <span className="text-gradient">Intelligence.</span>
              </h1>
              <p className="hero-copy">
                CVE/exploit intelligence feed with severity analysis, vendor tracking,
                and actionable security recommendations.
              </p>
            </section>
            <ThreatIntel />
          </div>
        )

      default:
        return <LandingPage onNavigate={navigate} />
    }
  }

  return (
    <main className="app-shell">
      <Starfield density={0.45} warp={route === '/' ? 0.01 : 0.005} shootingStars={route === '/'} />
      <NavBar active={route} onNavigate={navigate} />
      {renderPage()}
    </main>
  )
}

export default App
