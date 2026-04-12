import { useEffect, useMemo, useState } from 'react'

type Role = 'advisor' | 'admin'

type Message = {
  role: 'user' | 'assistant'
  content: string
}

type Conversation = {
  id: number
  title: string
  role: string
  messages: Message[]
}

type Citation = {
  title: string
  snippet: string
  source_type: string
}

type Stats = {
  total_conversations: number
  total_messages: number
  total_documents: number
  total_feedback: number
  positive_feedback: number
}

type FeedbackItem = {
  id: number
  conversation_id: number
  message_index: number
  value: number
}

type DocumentItem = {
  id: number
  title: string
  content: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

export default function App() {
  const [role, setRole] = useState<Role>('advisor')
  const [view, setView] = useState<'chat' | 'admin'>('chat')

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null)

  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lastCitations, setLastCitations] = useState<Record<number, Citation[]>>({})

  const [stats, setStats] = useState<Stats | null>(null)
  const [feedback, setFeedback] = useState<FeedbackItem[]>([])
  const [documents, setDocuments] = useState<DocumentItem[]>([])

  const [newDocTitle, setNewDocTitle] = useState('')
  const [newDocContent, setNewDocContent] = useState('')

  const selectedConversation = useMemo(
    () => conversations.find((c) => c.id === selectedConversationId) || null,
    [conversations, selectedConversationId],
  )

  async function fetchConversations() {
    const res = await fetch(`${API_BASE}/conversations`)
    const data = await res.json()
    setConversations(data)
    if (data.length > 0 && selectedConversationId === null) {
      setSelectedConversationId(data[0].id)
    }
  }

  async function fetchAdminData() {
    const [statsRes, feedbackRes, docsRes] = await Promise.all([
      fetch(`${API_BASE}/admin/stats`),
      fetch(`${API_BASE}/admin/feedback`),
      fetch(`${API_BASE}/documents`),
    ])

    setStats(await statsRes.json())
    setFeedback(await feedbackRes.json())
    setDocuments(await docsRes.json())
  }

  useEffect(() => {
    fetchConversations()
  }, [])

  useEffect(() => {
    if (role === 'admin') {
      fetchAdminData()
    }
  }, [role])

  async function sendMessage() {
    if (!input.trim()) return

    setLoading(true)
    setError('')

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: selectedConversationId,
          role,
          message: input,
        }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Request failed')
      }

      const data = await res.json()

      setLastCitations((prev) => ({
        ...prev,
        [data.conversation_id]: data.citations,
      }))

      setInput('')
      await fetchConversations()
      setSelectedConversationId(data.conversation_id)

      if (role === 'admin') {
        await fetchAdminData()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  async function submitFeedback(messageIndex: number, value: 1 | -1) {
    if (!selectedConversationId) return

    await fetch(`${API_BASE}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation_id: selectedConversationId,
        message_index: messageIndex,
        value,
      }),
    })

    if (role === 'admin') {
      await fetchAdminData()
    }
  }

  async function addDocument() {
    if (!newDocTitle.trim() || !newDocContent.trim()) return

    const res = await fetch(`${API_BASE}/documents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: newDocTitle, content: newDocContent }),
    })

    if (!res.ok) {
      const data = await res.json()
      alert(data.detail || 'Failed to ingest document')
      return
    }

    setNewDocTitle('')
    setNewDocContent('')
    await fetchAdminData()
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h2>AI Advising Assistant</h2>
        <p className="muted">Demo role-based MVP</p>

        <div className="profile-box">
          <label>Role</label>
          <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
            <option value="advisor">Advisor</option>
            <option value="admin">Admin</option>
          </select>

          <label>View</label>
          <select
            value={view}
            onChange={(e) => setView(e.target.value as 'chat' | 'admin')}
          >
            <option value="chat">Chat</option>
            {role === 'admin' && <option value="admin">Admin Dashboard</option>}
          </select>
        </div>
      </aside>

      <main className="content">
        {view === 'chat' && (
          <div className="chat-page">
            <section className="conversation-list">
              <div className="conversation-list-header">
                <h3>Conversations</h3>
                <button
                  onClick={() => {
                    setSelectedConversationId(null)
                    setInput('')
                  }}
                >
                  New
                </button>
              </div>

              {conversations.length === 0 && (
                <div className="empty-state">No conversations yet.</div>
              )}

              {conversations.map((conversation) => (
                <button
                  key={conversation.id}
                  className={`conversation-item ${
                    conversation.id === selectedConversationId ? 'active' : ''
                  }`}
                  onClick={() => setSelectedConversationId(conversation.id)}
                >
                  <strong>{conversation.title}</strong>
                  <span className="muted">
                    {conversation.messages.length} messages
                  </span>
                </button>
              ))}
            </section>

            <section className="chat-panel">
              <div className="chat-header">
                <h3>{selectedConversation ? selectedConversation.title : 'New Chat'}</h3>
                <p className="muted">
                  Ask about probation, transfer credit, graduation, or internal policy.
                </p>
              </div>

              <div className="messages">
                {!selectedConversation && (
                  <div className="empty-state">
                    Start a new conversation by asking a question below.
                  </div>
                )}

                {selectedConversation?.messages.map((message, index) => {
                  const isLastAssistant =
                    message.role === 'assistant' &&
                    index === selectedConversation.messages.length - 1

                  return (
                    <div key={index} className={`message ${message.role}`}>
                      <div className="message-role">{message.role.toUpperCase()}</div>
                      <div className="message-content">{message.content}</div>

                      {isLastAssistant &&
                        lastCitations[selectedConversation.id] &&
                        lastCitations[selectedConversation.id].length > 0 && (
                          <div className="citations">
                            <strong>Sources</strong>
                            {lastCitations[selectedConversation.id].map((citation, i) => (
                              <div className="citation" key={i}>
                                <div><strong>{citation.title}</strong></div>
                                <div>{citation.snippet}</div>
                              </div>
                            ))}
                          </div>
                        )}

                      {message.role === 'assistant' && (
                        <div className="feedback-row">
                          <button onClick={() => submitFeedback(index, 1)}>Helpful</button>
                          <button onClick={() => submitFeedback(index, -1)}>Not Helpful</button>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>

              {error && <div className="error">{error}</div>}

              <div className="composer">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask an advising question..."
                />
                <button onClick={sendMessage} disabled={loading}>
                  {loading ? 'Sending...' : 'Send'}
                </button>
              </div>
            </section>
          </div>
        )}

        {view === 'admin' && role === 'admin' && (
          <div className="admin-page">
            <h2>Admin Dashboard</h2>

            <div className="stats-grid">
              <div className="card">
                <span>Conversations</span>
                <strong>{stats?.total_conversations ?? 0}</strong>
              </div>
              <div className="card">
                <span>Messages</span>
                <strong>{stats?.total_messages ?? 0}</strong>
              </div>
              <div className="card">
                <span>Documents</span>
                <strong>{stats?.total_documents ?? 0}</strong>
              </div>
              <div className="card">
                <span>Feedback</span>
                <strong>{stats?.total_feedback ?? 0}</strong>
              </div>
              <div className="card">
                <span>Positive</span>
                <strong>{stats?.positive_feedback ?? 0}</strong>
              </div>
            </div>

            <div className="admin-grid">
              <div className="panel">
                <h3>Documents</h3>
                <div className="list">
                  {documents.map((doc) => (
                    <div key={doc.id} className="list-item">
                      <strong>{doc.title}</strong>
                      <div className="muted">{doc.content.slice(0, 140)}...</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="panel">
                <h3>Ingest Document</h3>
                <input
                  value={newDocTitle}
                  onChange={(e) => setNewDocTitle(e.target.value)}
                  placeholder="Document title"
                />
                <div style={{ height: 10 }} />
                <textarea
                  value={newDocContent}
                  onChange={(e) => setNewDocContent(e.target.value)}
                  placeholder="Paste document text"
                  rows={12}
                />
                <div style={{ height: 10 }} />
                <button onClick={addDocument}>Add Document</button>
              </div>

              <div className="panel">
                <h3>Feedback Log</h3>
                <div className="list">
                  {feedback.map((item) => (
                    <div key={item.id} className="list-item">
                      <div><strong>Conversation:</strong> {item.conversation_id}</div>
                      <div><strong>Message Index:</strong> {item.message_index}</div>
                      <div><strong>Value:</strong> {item.value === 1 ? 'Helpful' : 'Not Helpful'}</div>
                    </div>
                  ))}
                  {feedback.length === 0 && (
                    <div className="muted">No feedback submitted yet.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {view === 'admin' && role !== 'admin' && (
          <div className="empty-state">Switch your role to admin to view the dashboard.</div>
        )}
      </main>
    </div>
  )
}
