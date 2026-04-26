import { useEffect, useMemo, useState, type CSSProperties } from 'react'

type Role = 'member' | 'admin'

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
  category: string
}

type ProviderStatus = {
  provider: string
  model: string
  configured: boolean
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

export default function App() {
  const [role, setRole] = useState<Role>('member')
  const [view, setView] = useState<'chat' | 'admin'>('chat')
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null)
  const [conversationSearch, setConversationSearch] = useState('')
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lastCitations, setLastCitations] = useState<Record<number, Citation[]>>({})

  const [stats, setStats] = useState<Stats | null>(null)
  const [feedback, setFeedback] = useState<FeedbackItem[]>([])
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null)

  const [newDocTitle, setNewDocTitle] = useState('')
  const [newDocCategory, setNewDocCategory] = useState('General')
  const [newDocContent, setNewDocContent] = useState('')
  const [docStatus, setDocStatus] = useState('')
  const [scrollOffset, setScrollOffset] = useState(0)

  const selectedConversation = useMemo(
    () => conversations.find((c) => c.id === selectedConversationId) || null,
    [conversations, selectedConversationId]
  )

  const filteredConversations = useMemo(() => {
    const query = conversationSearch.trim().toLowerCase()
    if (!query) {
      return conversations
    }

    return conversations.filter((conversation) => {
      const haystack = `${conversation.title} ${conversation.messages
        .map((message) => message.content)
        .join(' ')}`.toLowerCase()
      return haystack.includes(query)
    })
  }, [conversationSearch, conversations])

  async function fetchConversations() {
    const res = await fetch(`${API_BASE}/conversations`)
    const data = await res.json()
    setConversations(data)
    if (selectedConversationId === null && data.length > 0) {
      setSelectedConversationId(data[0].id)
    }
  }

  async function fetchAdminData() {
    const [statsRes, feedbackRes, docsRes, providerRes] = await Promise.all([
      fetch(`${API_BASE}/admin/stats`),
      fetch(`${API_BASE}/admin/feedback`),
      fetch(`${API_BASE}/documents`),
      fetch(`${API_BASE}/admin/provider-status`)
    ])

    setStats(await statsRes.json())
    setFeedback(await feedbackRes.json())
    setDocuments(await docsRes.json())
    setProviderStatus(await providerRes.json())
  }

  useEffect(() => {
    fetchConversations()
  }, [])

  useEffect(() => {
    if (role === 'admin') {
      fetchAdminData()
    }
  }, [role])

  useEffect(() => {
    const handleScroll = () => {
      setScrollOffset(window.scrollY)
    }

    handleScroll()
    window.addEventListener('scroll', handleScroll, { passive: true })

    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

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
          message: input
        })
      })

      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Request failed')
      }

      setLastCitations((prev) => ({
        ...prev,
        [data.conversation_id]: data.citations
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
        value
      })
    })

    if (role === 'admin') {
      await fetchAdminData()
    }
  }

  async function addDocument() {
    if (role !== 'admin') {
      setDocStatus('Only admins can add documents.')
      return
    }

    if (!newDocTitle.trim() || !newDocContent.trim()) return

    const res = await fetch(`${API_BASE}/documents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        role,
        title: newDocTitle,
        category: newDocCategory,
        content: newDocContent
      })
    })

    const data = await res.json()
    if (!res.ok) {
      setDocStatus(data.detail || 'Failed to add document')
      return
    }

    setNewDocTitle('')
    setNewDocCategory('General')
    setNewDocContent('')
    setDocStatus('Document added to the knowledge base.')
    await fetchAdminData()
  }

  async function deleteConversation(conversationId: number) {
    const confirmed = window.confirm('Delete this conversation permanently?')
    if (!confirmed) return

    try {
      const res = await fetch(`${API_BASE}/conversations/${conversationId}`, {
        method: 'DELETE'
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to delete conversation')
      }

      if (selectedConversationId === conversationId) {
        setSelectedConversationId(null)
      }

      setLastCitations((prev) => {
        const next = { ...prev }
        delete next[conversationId]
        return next
      })

      await fetchConversations()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  return (
    <div
      className="shell"
      style={
        {
          '--scroll-shift': `${scrollOffset * 0.35}px`,
          '--scroll-shift-soft': `${scrollOffset * 0.18}px`
        } as CSSProperties
      }
    >
      <div className="background-orbit orbit-one" />
      <div className="background-orbit orbit-two" />
      <div className="background-grid" />
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />
      <div className="ambient ambient-c" />

      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">AI</div>
          <div>
            <p className="brand-kicker">Internal AI</p>
            <h1>AIvising</h1>
          </div>
        </div>

        <p className="sidebar-copy">
          Answers grounded in team docs, workflows, policies, and support playbooks.
        </p>

        <div className="sidebar-section">
          <label className="field-label">Role</label>
          <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
            <option value="member">Member</option>
            <option value="admin">Admin</option>
          </select>
        </div>

        <div className="sidebar-section">
          <label className="field-label">Workspace</label>
          <div className="workspace-card">
            <div className="workspace-title">Operations Knowledge Base</div>
            <div className="workspace-subtitle">Starter docs, admin insights, live feedback</div>
          </div>
        </div>

        <div className="sidebar-section nav-stack">
          <button
            className={`ghost-btn ${view === 'chat' ? 'active' : ''}`}
            onClick={() => setView('chat')}
          >
            <span>Chat</span>
            <small>Conversations and retrieval</small>
          </button>

          {role === 'admin' && (
            <button
              className={`ghost-btn ${view === 'admin' ? 'active' : ''}`}
              onClick={() => setView('admin')}
            >
              <span>Admin Dashboard</span>
              <small>Documents, feedback, analytics</small>
            </button>
          )}
        </div>

        <div className="sidebar-footer">
          <div className="status-dot" />
          Retrieval ready and demo friendly
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <div className="eyebrow">Workspace Assistant</div>
            <h2>{view === 'chat' ? 'AIvising Chat' : 'AIvising Control Center'}</h2>
            <p className="topbar-copy">
              {view === 'chat'
                ? 'Ask grounded questions across your internal knowledge base.'
                : 'Monitor content quality, feedback trends, and document coverage.'}
            </p>
          </div>

          <div className="topbar-actions">
            <button
              className="secondary-btn"
              onClick={() => {
                setSelectedConversationId(null)
                setInput('')
              }}
            >
              New chat
            </button>
          </div>
        </header>

        {view === 'chat' && (
          <div className="layout">
            <section className="panel conversation-panel">
              <div className="panel-header">
                <div>
                  <h3>Recent chats</h3>
                  <p className="panel-copy">Your latest internal knowledge sessions.</p>
                </div>
                <span className="pill">{conversations.length}</span>
              </div>

              <div className="conversation-list">
                <input
                  value={conversationSearch}
                  onChange={(e) => setConversationSearch(e.target.value)}
                  placeholder="Search conversations..."
                  className="conversation-search"
                />

                {conversations.length === 0 && (
                  <div className="empty-card">
                    No conversations yet. Start by asking a policy or process question.
                  </div>
                )}

                {conversations.length > 0 && filteredConversations.length === 0 && (
                  <div className="empty-card">No conversations match that search.</div>
                )}

                {filteredConversations.map((conversation) => (
                  <div
                    key={conversation.id}
                    className={`conversation-row ${
                      selectedConversationId === conversation.id ? 'active' : ''
                    }`}
                  >
                    <button
                      className="conversation-select"
                      onClick={() => setSelectedConversationId(conversation.id)}
                    >
                      <div className="conversation-title">{conversation.title}</div>
                      <div className="conversation-meta">{conversation.messages.length} messages</div>
                    </button>
                    <button
                      className="conversation-delete"
                      onClick={() => deleteConversation(conversation.id)}
                      aria-label={`Delete conversation ${conversation.title}`}
                      title="Delete conversation"
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            </section>

            <section className="panel chat-panel">
              <div className="panel-header">
                <div>
                  <h3>{selectedConversation ? selectedConversation.title : 'New conversation'}</h3>
                  <div className="subtle-text">
                    Ask about onboarding, incident response, team workflows, and internal guidance.
                  </div>
                </div>
              </div>

              <div className="messages">
                {!selectedConversation && (
                  <div className="welcome-card hero-card">
                    <div className="hero-copy">
                      <span className="hero-pill">AIvising Workspace</span>
                      <h3>Built for fast, grounded answers.</h3>
                      <p>
                        Search policies, onboarding materials, support playbooks, and operating
                        procedures through a cleaner internal assistant experience.
                      </p>
                    </div>

                    <div className="prompt-grid">
                      <button
                        className="prompt-card"
                        onClick={() => setInput('How does our incident escalation process work?')}
                      >
                        How does our incident escalation process work?
                      </button>
                      <button
                        className="prompt-card"
                        onClick={() => setInput('What should a new hire complete in week one?')}
                      >
                        What should a new hire complete in week one?
                      </button>
                      <button
                        className="prompt-card"
                        onClick={() => setInput('What should be included in a design review?')}
                      >
                        What should be included in a design review?
                      </button>
                    </div>
                  </div>
                )}

                {selectedConversation?.messages.map((message, index) => {
                  const isLastAssistant =
                    message.role === 'assistant' &&
                    index === selectedConversation.messages.length - 1

                  return (
                    <div
                      key={index}
                      className={`message-bubble ${message.role === 'user' ? 'user' : 'assistant'}`}
                    >
                      <div className="message-label">
                        {message.role === 'user' ? 'You' : 'Assistant'}
                      </div>
                      <div className="message-text">{message.content}</div>

                      {isLastAssistant && lastCitations[selectedConversation.id] && (
                        <div className="source-block">
                          <div className="source-title">Sources</div>
                          {lastCitations[selectedConversation.id].map((citation, i) => (
                            <div key={i} className="source-card">
                              <strong>{citation.title}</strong>
                              <div>{citation.snippet}</div>
                            </div>
                          ))}
                        </div>
                      )}

                      {message.role === 'assistant' && (
                        <div className="feedback-actions">
                          <button className="mini-btn" onClick={() => submitFeedback(index, 1)}>
                            Helpful
                          </button>
                          <button className="mini-btn" onClick={() => submitFeedback(index, -1)}>
                            Not helpful
                          </button>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>

              {error && <div className="error-banner">{error}</div>}

              <div className="composer">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a question about internal processes, docs, or policies..."
                />
                <button className="primary-btn" onClick={sendMessage} disabled={loading}>
                  {loading ? 'Sending...' : 'Send'}
                </button>
              </div>
            </section>
          </div>
        )}

        {view === 'admin' && role === 'admin' && (
          <div className="admin-layout">
            <div className="metric-grid">
              <div className="metric-card">
                <span>Conversations</span>
                <strong>{stats?.total_conversations ?? 0}</strong>
              </div>
              <div className="metric-card">
                <span>Messages</span>
                <strong>{stats?.total_messages ?? 0}</strong>
              </div>
              <div className="metric-card">
                <span>Documents</span>
                <strong>{stats?.total_documents ?? 0}</strong>
              </div>
              <div className="metric-card">
                <span>Feedback</span>
                <strong>{stats?.total_feedback ?? 0}</strong>
              </div>
              <div className="metric-card">
                <span>Positive feedback</span>
                <strong>{stats?.positive_feedback ?? 0}</strong>
              </div>
            </div>

            <div className="admin-grid">
              <section className="panel">
                <div className="panel-header">
                  <div>
                    <h3>Provider status</h3>
                    <p className="panel-copy">Current inference provider and model configuration.</p>
                  </div>
                </div>
                <div className="form-stack">
                  <div className="doc-card">
                    <div className="doc-top">
                      <strong>{providerStatus?.provider ?? 'unknown'}</strong>
                      <span className="tag">
                        {providerStatus?.configured ? 'Configured' : 'Not configured'}
                      </span>
                    </div>
                    <p>{providerStatus?.model ?? 'No model loaded'}</p>
                  </div>
                </div>
              </section>

              <section className="panel">
                <div className="panel-header">
                  <div>
                    <h3>Knowledge base</h3>
                    <p className="panel-copy">Current internal documents available to retrieval.</p>
                  </div>
                </div>
                <div className="document-grid">
                  {documents.map((doc) => (
                    <div key={doc.id} className="doc-card">
                      <div className="doc-top">
                        <strong>{doc.title}</strong>
                        <span className="tag">{doc.category}</span>
                      </div>
                      <p>{doc.content}</p>
                    </div>
                  ))}
                </div>
              </section>

              <section className="panel">
                <div className="panel-header">
                  <div>
                    <h3>Add document</h3>
                    <p className="panel-copy">Ingest new policy, SOP, or support reference.</p>
                  </div>
                </div>
                <div className="form-stack">
                  <div>
                    <label className="field-label">Title</label>
                    <input
                      value={newDocTitle}
                      onChange={(e) => setNewDocTitle(e.target.value)}
                      placeholder="e.g. PTO Request Procedure"
                    />
                  </div>

                  <div>
                    <label className="field-label">Category</label>
                    <input
                      value={newDocCategory}
                      onChange={(e) => setNewDocCategory(e.target.value)}
                      placeholder="General"
                    />
                  </div>

                  <div>
                    <label className="field-label">Content</label>
                    <textarea
                      rows={10}
                      value={newDocContent}
                      onChange={(e) => setNewDocContent(e.target.value)}
                      placeholder="Paste a policy, process, or reference document..."
                    />
                  </div>

                  <button className="primary-btn" onClick={addDocument}>
                    Save document
                  </button>

                  {docStatus && <div className="subtle-text">{docStatus}</div>}
                </div>
              </section>

              <section className="panel">
                <div className="panel-header">
                  <div>
                    <h3>Feedback activity</h3>
                    <p className="panel-copy">Recent signal on answer quality.</p>
                  </div>
                </div>
                <div className="feedback-list">
                  {feedback.length === 0 && <div className="empty-card">No feedback yet.</div>}
                  {feedback.map((item) => (
                    <div key={item.id} className="feedback-item">
                      <div>
                        <strong>Conversation #{item.conversation_id}</strong>
                      </div>
                      <div>Message index: {item.message_index}</div>
                      <div>Status: {item.value === 1 ? 'Helpful' : 'Not helpful'}</div>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
