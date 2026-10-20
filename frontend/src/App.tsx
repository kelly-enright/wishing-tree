import { Route, Routes } from 'react-router-dom'
import Coordinator from './pages/Coordinator'
import Donor from './pages/Donor'
import Intake from './pages/Intake'
import Landing from './pages/Landing'
import Placeholder from './pages/Placeholder'
import SignUpDonor from './pages/SignUpDonor'
import SignUpFamily from './pages/SignUpFamily'

/**
 * Three ways in: family sign-up, donor sign-up, and the coordinator passcode.
 * The role screens behind them are placeholders until the problems that build them.
 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/family/signup" element={<SignUpFamily />} />
      <Route path="/family" element={<Intake />} />
      <Route path="/donor/signup" element={<SignUpDonor />} />
      <Route path="/donor" element={<Donor />} />
      <Route path="/coordinator" element={<Coordinator />} />
      <Route
        path="*"
        element={<Placeholder title="Page not found" blurb="That page does not exist." />}
      />
    </Routes>
  )
}
