import { useState } from "react";
import { Login } from "./components/Login";
import Dashboard from "./Dashboard";

export default function App() {
  const [user, setUser] = useState<string | null>(null);

  if (!user) {
    return <Login onLogin={setUser} />;
  }

  return <Dashboard userName={user} onLogout={() => setUser(null)} />;
}
