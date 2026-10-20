import { Route, Routes } from 'react-router-dom'
import Landing from './pages/Landing'
import Placeholder from './pages/Placeholder'

/**
 * Routes for the MVP. The landing page is real; the three role screens are
 * placeholders until the problems that build them.
 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route
        path="/family"
        element={
          <Placeholder
            title="I need help"
            blurb="This is where a family will chat with the Intake agent, approve each wish before it is submitted, and confirm a delivery window."
          />
        }
      />
      <Route
        path="/family/demo"
        element={
          <Placeholder
            title="Seeded family (demo)"
            blurb="This opens one of the seeded demo families so the flow can be shown without signing up first."
          />
        }
      />
      <Route
        path="/donor"
        element={
          <Placeholder
            title="I want to give"
            blurb="This is where a donor will set their zip, budget and categories, browse the wish wall or get matched, grant a wish, and pick a weekly drop-off."
          />
        }
      />
      <Route
        path="/coordinator"
        element={
          <Placeholder
            title="Coordinator"
            blurb="This is where the coordinator will see the weekly run sheet of expected drop-offs and deliveries, with contact details and statuses."
          />
        }
      />
      <Route
        path="*"
        element={<Placeholder title="Page not found" blurb="That page does not exist yet." />}
      />
    </Routes>
  )
}
