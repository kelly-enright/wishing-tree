import { Route, Routes } from 'react-router-dom'
import About from './pages/About'
import Coordinator from './pages/Coordinator'
import Donor from './pages/Donor'
import Intake from './pages/Intake'
import Landing from './pages/Landing'
import LogIn from './pages/LogIn'
import ChooseSide from './pages/ChooseSide'
import Forgot from './pages/Forgot'
import HowItWorksPage from './pages/HowItWorksPage'
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
      <Route path="/about" element={<About />} />
      <Route path="/how-it-works" element={<HowItWorksPage />} />
      <Route path="/login" element={<LogIn />} />
      <Route path="/choose" element={<ChooseSide />} />
      <Route path="/forgot" element={<Forgot />} />
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
