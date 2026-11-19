import { Link, Route, Routes } from "react-router-dom";
import RequestForm from "./pages/RequestForm.jsx";
import Status from "./pages/Status.jsx";
import Chat from "./pages/Chat.jsx";
import Admin from "./pages/Admin.jsx";

export default function App() {
  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand" aria-label="RentVoice home">
          <span className="brand-mark" aria-hidden="true">
            <i /><i /><i /><i />
          </span>
          RentVoice
        </Link>
        <nav>
          <Link to="/admin">For owners</Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<RequestForm />} />
          <Route path="/requests/:id" element={<Status />} />
          <Route path="/chat/:token" element={<Chat />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="*" element={<p className="empty">This page doesn't exist. <Link to="/">Start a new search</Link>.</p>} />
        </Routes>
      </main>
    </div>
  );
}
