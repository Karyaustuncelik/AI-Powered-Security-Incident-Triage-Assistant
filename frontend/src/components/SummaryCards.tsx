type SummaryCard = {
  label: string
  value: string
  note: string
}

type SummaryCardsProps = {
  cards: SummaryCard[]
}

export function SummaryCards({ cards }: SummaryCardsProps) {
  return (
    <section className="summary-grid">
      {cards.map((card) => (
        <article key={card.label} className="summary-card">
          <span className="summary-label">{card.label}</span>
          <strong className="summary-value">{card.value}</strong>
          <span className="summary-note">{card.note}</span>
        </article>
      ))}
    </section>
  )
}
