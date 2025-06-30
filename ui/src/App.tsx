import { ChatContainer } from './components/ChatContainer'
import './App.css'

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Executive AI</h1>
        <p>AI-powered candidate analysis assistant</p>
      </header>
      <main className="app-main">
        <ChatContainer />
      </main>
    </div>
  )
}

export default App