import { Link } from 'react-router-dom'

export default function HomePage() {
  return (
    <div className="home">
      <h2 className="home-title">Ask years of IT tickets a question.</h2>
      <p className="home-text">
        Search real support tickets by meaning, and get answers from Claude that cite the exact tickets they
        came from. If nothing matches well enough, it says so instead of guessing.
      </p>

      <div className="home-cards">
        <Link to="/ask" className="home-card">
          <span className="home-card-title">Ask →</span>
          <span>Ask a question and get an answer with cited source tickets.</span>
        </Link>
        <Link to="/browse" className="home-card">
          <span className="home-card-title">Browse →</span>
          <span>Search and filter every ticket by keyword and category.</span>
        </Link>
      </div>
    </div>
  )
}
