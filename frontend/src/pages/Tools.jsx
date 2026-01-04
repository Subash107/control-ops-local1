import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api.js'
import Modal from '../components/Modal.jsx'

function parseTags(text) {
  return Array.from(
    new Set(
      (text || '')
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean)
    )
  )
}

function fmtDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  return d.toLocaleString()
}

function SortHeader({ label, active, dir, rank, onClick, width }) {
  const arrow = active ? (dir === 'asc' ? '▲' : '▼') : ''
  const badge = active ? (rank > 0 ? `${rank}${arrow}` : arrow) : ''
  return (
    <th style={width ? { width } : undefined}>
      <span
        className="sortHeader"
        onClick={onClick}
        role="button"
        tabIndex={0}
        title="Click to make this the primary sort (toggles direction if already primary)"
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick() }}
      >
        {label} {badge}
      </span>
    </th>
  )
}

const SORT_FIELDS = [
  { by: 'created_at', label: 'Created' },
  { by: 'name', label: 'Name' },
  { by: 'category', label: 'Category' }
]

const SORT_PRESETS = [
  { key: 'created_desc', label: 'Created (newest)', spec: [{ by: 'created_at', dir: 'desc' }] },
  { key: 'created_asc', label: 'Created (oldest)', spec: [{ by: 'created_at', dir: 'asc' }] },
  { key: 'name_asc', label: 'Name (A–Z)', spec: [{ by: 'name', dir: 'asc' }] },
  { key: 'name_desc', label: 'Name (Z–A)', spec: [{ by: 'name', dir: 'desc' }] },
  { key: 'cat_name', label: 'Category → Name', spec: [{ by: 'category', dir: 'asc' }, { by: 'name', dir: 'asc' }] },
  { key: 'cat_created', label: 'Category → Created', spec: [{ by: 'category', dir: 'asc' }, { by: 'created_at', dir: 'desc' }] }
]

function specToQuery(spec) {
  return (spec || []).map((s) => `${s.by}:${s.dir}`).join(',')
}

function defaultDir(field) {
  return field === 'created_at' ? 'desc' : 'asc'
}

function normalizeSpec(spec) {
  const seen = new Set()
  const cleaned = []
  for (const s of spec || []) {
    if (!s?.by) continue
    if (seen.has(s.by)) continue
    seen.add(s.by)
    cleaned.push({ by: s.by, dir: s.dir === 'asc' ? 'asc' : 'desc' })
  }
  return cleaned.slice(0, 3)
}

function pickFromSpec(spec, idx, fallbackBy, fallbackDir) {
  const s = (spec || [])[idx]
  if (!s?.by) return { by: fallbackBy, dir: fallbackDir }
  return { by: s.by, dir: s.dir === 'asc' ? 'asc' : 'desc' }
}

function reorder(list, from, to) {
  const next = [...list]
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  return next
}

export default function Tools({ isAdmin }) {
  const [tools, setTools] = useState([])
  const [total, setTotal] = useState(0)
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modal, setModal] = useState(null)

  const [categoryFilter, setCategoryFilter] = useState('')
  const [tagFilter, setTagFilter] = useState('')
  const [q, setQ] = useState('')

  const [limit, setLimit] = useState(20)
  const [offset, setOffset] = useState(0)

  // Multi-column sort state.
  const [sortPreset, setSortPreset] = useState('created_desc')
  const [sortSpec, setSortSpec] = useState(SORT_PRESETS[0].spec)

  // Drag/drop priority reordering (badges)
  const [dragIndex, setDragIndex] = useState(null)

  const page = useMemo(() => Math.floor(offset / limit) + 1, [offset, limit])
  const pages = useMemo(() => Math.max(1, Math.ceil((total || 0) / limit)), [total, limit])

  function setPreset(key) {
    const preset = SORT_PRESETS.find((p) => p.key === key) || SORT_PRESETS[0]
    setSortPreset(preset.key)
    setSortSpec(normalizeSpec(preset.spec))
  }

  function clearSort() {
    setPreset('created_desc')
  }

  function setSortBuilder(primaryBy, primaryDir, secondaryBy, secondaryDir, tertiaryBy, tertiaryDir) {
    setSortPreset('custom')
    const next = [
      { by: primaryBy, dir: primaryDir || defaultDir(primaryBy) }
    ]
    if (secondaryBy && secondaryBy !== primaryBy) {
      next.push({ by: secondaryBy, dir: secondaryDir || defaultDir(secondaryBy) })
    }
    if (tertiaryBy && tertiaryBy !== primaryBy && tertiaryBy !== secondaryBy) {
      next.push({ by: tertiaryBy, dir: tertiaryDir || defaultDir(tertiaryBy) })
    }
    setSortSpec(normalizeSpec(next))
  }

  function toggleSort(field) {
    setSortPreset('custom')
    setSortSpec((prev) => {
      const next = [...(prev || [])]
      const idx = next.findIndex((s) => s.by === field)
      if (idx === 0) {
        next[0] = { ...next[0], dir: next[0].dir === 'asc' ? 'desc' : 'asc' }
        return normalizeSpec(next)
      }
      if (idx > 0) {
        const [found] = next.splice(idx, 1)
        next.unshift(found)
        return normalizeSpec(next)
      }
      const primary = { by: field, dir: defaultDir(field) }
      return normalizeSpec([primary, ...next])
    })
  }

  function sortRank(field) {
    const i = (sortSpec || []).findIndex((s) => s.by === field)
    return i >= 0 ? i + 1 : 0
  }

  function sortDir(field) {
    const s = (sortSpec || []).find((x) => x.by === field)
    return s?.dir || 'asc'
  }

  const primary = useMemo(() => pickFromSpec(sortSpec, 0, 'created_at', 'desc'), [sortSpec])
  const secondary = useMemo(() => pickFromSpec(sortSpec, 1, '', 'asc'), [sortSpec])
  const tertiary = useMemo(() => pickFromSpec(sortSpec, 2, '', 'asc'), [sortSpec])

  function availableForSecondary() {
    return SORT_FIELDS.filter((f) => f.by !== primary.by)
  }

  function availableForTertiary() {
    return SORT_FIELDS.filter((f) => f.by !== primary.by && f.by !== secondary.by)
  }

  function onBadgeDragStart(i) {
    setDragIndex(i)
  }

  function onBadgeDrop(i) {
    setSortPreset('custom')
    setSortSpec((prev) => {
      if (dragIndex === null || dragIndex === i) return prev
      return normalizeSpec(reorder(prev || [], dragIndex, i))
    })
    setDragIndex(null)
  }

  async function load() {
    setLoading(true)
    setError('')
    try {
      const res = await api.get('/tools', {
        params: {
          category: categoryFilter || undefined,
          tag: tagFilter || undefined,
          q: q || undefined,
          limit,
          offset,
          sort: specToQuery(sortSpec)
        }
      })
      setTools(res.data.items || [])
      setTotal(res.data.total || 0)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load tools')
    } finally {
      setLoading(false)
    }
  }

  async function loadCategories() {
    try {
      const res = await api.get('/tools/categories')
      setCategories(res.data || [])
    } catch {
      setCategories([])
    }
  }

  useEffect(() => {
    loadCategories()
  }, [])

  // Reset pagination when filters/search/page-size/sort changes
  useEffect(() => {
    setOffset(0)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoryFilter, tagFilter, q, limit, sortPreset, sortSpec])

  useEffect(() => {
    const t = setTimeout(() => {
      load()
    }, 200)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoryFilter, tagFilter, q, limit, offset, sortPreset, sortSpec])

  function openCreate() {
    setModal({
      mode: 'create',
      tool: { name: '', description: '', url: '', category: 'general', tagsText: '' }
    })
  }

  function openEdit(tool) {
    setModal({
      mode: 'edit',
      tool: {
        id: tool.id,
        name: tool.name,
        description: tool.description,
        url: tool.url,
        category: tool.category || 'general',
        tagsText: (tool.tags || []).join(', ')
      }
    })
  }

  const [formErrors, setFormErrors] = useState({})
  const [isSaving, setIsSaving] = useState(false)

  function validateTool(t) {
    const errs = {}
    if (!t.name || t.name.trim().length < 2) errs.name = 'Name is required (min 2 chars)'
    if (t.name && t.name.length > 120) errs.name = 'Name too long (max 120 chars)'
    if (t.category && t.category.trim().length === 0) errs.category = 'Category required'
    if (t.url && t.url.trim().length > 0) {
      try {
        // allow missing scheme, auto-prefix https for client-side validation
        const u = t.url.includes('://') ? t.url : `https://${t.url}`
        new URL(u)
      } catch (err) {
        errs.url = 'Invalid URL'
      }
    }
    if (t.description && t.description.length > 5000) errs.description = 'Description too long'
    return errs
  }

  async function save() {
    setError('')
    setFormErrors({})

    const payload = {
      name: modal.tool.name,
      description: modal.tool.description,
      url: modal.tool.url,
      category: modal.tool.category || 'general',
      tags: parseTags(modal.tool.tagsText)
    }

    const errs = validateTool(payload)
    if (Object.keys(errs).length) {
      setFormErrors(errs)
      return
    }

    try {
      setIsSaving(true)
      if (modal.mode === 'create') {
        await api.post('/tools', payload)
      } else {
        await api.put(`/tools/${modal.tool.id}`, payload)
      }
      setModal(null)
      await loadCategories()
      await load()
    } catch (e) {
      const status = e?.response?.status
      const data = e?.response?.data
      if (status === 409 && data?.field && data?.message) {
        // structured duplicate error from server
        setFormErrors({ [data.field]: data.message })
      } else if (data?.detail) {
        setError(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
      } else {
        setError('Failed to save tool')
      }
    } finally {
      setIsSaving(false)
    }
  }

  async function remove(tool) {
    setError('')
    try {
      await api.delete(`/tools/${tool.id}`)
      await loadCategories()
      await load()
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to delete tool')
    }
  }

  const filtersActive = useMemo(() => !!(categoryFilter || tagFilter || q), [categoryFilter, tagFilter, q])

  const canPrev = offset > 0
  const canNext = offset + limit < total

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontWeight: 800, fontSize: 18 }}>Tools</div>
          <div className="small">Users can view tools. Admin can create/update/delete.</div>
        </div>
        {isAdmin ? <button className="btn" onClick={openCreate}>New Tool</button> : null}
      </div>

      <div className="row" style={{ marginTop: 12, alignItems: 'end' }}>
        <div style={{ minWidth: 220 }}>
          <div className="label">Category</div>
          <select className="input" value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
            <option value="">All</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div style={{ minWidth: 220, flex: 1 }}>
          <div className="label">Tag</div>
          <input className="input" value={tagFilter} onChange={(e) => setTagFilter(e.target.value)} placeholder="e.g. terraform" />
        </div>

        <div style={{ minWidth: 240, flex: 1 }}>
          <div className="label">Search</div>
          <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name / description / category" />
        </div>

        <div style={{ minWidth: 170 }}>
          <div className="label">Sort preset</div>
          <select className="input" value={sortPreset} onChange={(e) => setPreset(e.target.value)}>
            {SORT_PRESETS.map((p) => (
              <option key={p.key} value={p.key}>{p.label}</option>
            ))}
            <option value="custom">Custom</option>
          </select>
        </div>

        <div style={{ minWidth: 160 }}>
          <div className="label">Page size</div>
          <select className="input" value={limit} onChange={(e) => setLimit(parseInt(e.target.value, 10))}>
            {[10, 20, 50, 100].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>

        <button className="btn secondary" disabled={!filtersActive} onClick={() => { setCategoryFilter(''); setTagFilter(''); setQ('') }}>
          Clear filters
        </button>

        <button className="btn secondary" onClick={clearSort} title="Reset sorting to Created (newest)">
          Clear sort
        </button>
      </div>

      {/* Sort builder (primary/secondary/tertiary) */}
      <div className="row" style={{ marginTop: 10, alignItems: 'end' }}>
        <div style={{ minWidth: 220 }}>
          <div className="label">Primary sort</div>
          <select
            className="input"
            value={primary.by}
            onChange={(e) => setSortBuilder(e.target.value, primary.dir, secondary.by, secondary.dir, tertiary.by, tertiary.dir)}
          >
            {SORT_FIELDS.map((f) => <option key={f.by} value={f.by}>{f.label}</option>)}
          </select>
        </div>

        <div style={{ minWidth: 140 }}>
          <div className="label">Direction</div>
          <select
            className="input"
            value={primary.dir}
            onChange={(e) => setSortBuilder(primary.by, e.target.value, secondary.by, secondary.dir, tertiary.by, tertiary.dir)}
          >
            <option value="asc">Asc</option>
            <option value="desc">Desc</option>
          </select>
        </div>

        <div style={{ minWidth: 220 }}>
          <div className="label">Secondary sort</div>
          <select
            className="input"
            value={secondary.by || ''}
            onChange={(e) => setSortBuilder(primary.by, primary.dir, e.target.value || '', secondary.dir, tertiary.by, tertiary.dir)}
          >
            <option value="">None</option>
            {availableForSecondary().map((f) => (
              <option key={f.by} value={f.by}>{f.label}</option>
            ))}
          </select>
        </div>

        <div style={{ minWidth: 140 }}>
          <div className="label">Direction</div>
          <select
            className="input"
            value={secondary.by ? secondary.dir : 'asc'}
            disabled={!secondary.by}
            onChange={(e) => setSortBuilder(primary.by, primary.dir, secondary.by, e.target.value, tertiary.by, tertiary.dir)}
          >
            <option value="asc">Asc</option>
            <option value="desc">Desc</option>
          </select>
        </div>

        <div style={{ minWidth: 220 }}>
          <div className="label">Tertiary sort</div>
          <select
            className="input"
            value={tertiary.by || ''}
            disabled={!secondary.by}
            onChange={(e) => setSortBuilder(primary.by, primary.dir, secondary.by, secondary.dir, e.target.value || '', tertiary.dir)}
          >
            <option value="">None</option>
            {availableForTertiary().map((f) => (
              <option key={f.by} value={f.by}>{f.label}</option>
            ))}
          </select>
        </div>

        <div style={{ minWidth: 140 }}>
          <div className="label">Direction</div>
          <select
            className="input"
            value={tertiary.by ? tertiary.dir : 'asc'}
            disabled={!secondary.by || !tertiary.by}
            onChange={(e) => setSortBuilder(primary.by, primary.dir, secondary.by, secondary.dir, tertiary.by, e.target.value)}
          >
            <option value="asc">Asc</option>
            <option value="desc">Desc</option>
          </select>
        </div>

        <div className="small" style={{ alignSelf: 'center', opacity: 0.85 }}>
          Tip: drag badges to reorder priorities (1/2/3).
        </div>
      </div>

      {/* Current sort badges (drag to reorder) */}
      <div className="row" style={{ marginTop: 10, alignItems: 'center' }}>
        <div className="small" style={{ opacity: 0.9 }}>Current sort:</div>
        <div className="sortBadges">
          {(sortSpec || []).length ? (
            (sortSpec || []).map((s, idx) => (
              <span
                key={`${s.by}-${idx}`}
                className={`badge draggableBadge ${dragIndex === idx ? 'dragging' : ''}`}
                title="Drag to reorder priority"
                draggable
                onDragStart={() => onBadgeDragStart(idx)}
                onDragEnd={() => setDragIndex(null)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => onBadgeDrop(idx)}
              >
                {idx + 1}) {s.by} {s.dir}
              </span>
            ))
          ) : (
            <span className="small">—</span>
          )}
        </div>
      </div>

      <div className="row" style={{ marginTop: 12, justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="small">
          Showing <strong>{total ? Math.min(total, offset + 1) : 0}</strong>–<strong>{Math.min(total, offset + limit)}</strong> of <strong>{total}</strong>
        </div>
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <button className="btn secondary" disabled={!canPrev} onClick={() => setOffset(Math.max(0, offset - limit))}>Prev</button>
          <span className="badge" title="Current page">{page} / {pages}</span>
          <button className="btn secondary" disabled={!canNext} onClick={() => setOffset(offset + limit)}>Next</button>
        </div>
      </div>

      {error ? <div style={{ color: '#fca5a5', marginTop: 12 }}>{error}</div> : null}
      {loading ? <div style={{ marginTop: 12 }}>Loading...</div> : null}

      {!loading ? (
        <div style={{ marginTop: 12, overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr>
                <SortHeader label="Name" width={220} active={sortRank('name') > 0} dir={sortDir('name')} rank={sortRank('name')} onClick={() => toggleSort('name')} />
                <SortHeader label="Category" width={160} active={sortRank('category') > 0} dir={sortDir('category')} rank={sortRank('category')} onClick={() => toggleSort('category')} />
                <th>Description</th>
                <th style={{ width: 240 }}>Tags</th>
                <th style={{ width: 280 }}>URL</th>
                <SortHeader label="Created" width={220} active={sortRank('created_at') > 0} dir={sortDir('created_at')} rank={sortRank('created_at')} onClick={() => toggleSort('created_at')} />
                {isAdmin ? <th style={{ width: 160 }} /> : null}
              </tr>
            </thead>
            <tbody>
              {tools.map((t) => (
                <tr key={t.id}>
                  <td><strong>{t.name}</strong></td>
                  <td><span className="badge">{t.category || 'general'}</span></td>
                  <td>{t.description}</td>
                  <td>
                    <div className="chips">
                      {(t.tags || []).length ? (
                        (t.tags || []).map((tag) => (
                          <span
                            key={tag}
                            className={`chip ${tagFilter === tag ? 'active' : ''}`}
                            title="Click to filter by this tag"
                            onClick={() => setTagFilter(tag)}
                          >
                            {tag}
                          </span>
                        ))
                      ) : (
                        <span className="small">—</span>
                      )}
                    </div>
                  </td>
                  <td>
                    {t.url ? (
                      <a href={t.url} target="_blank" rel="noreferrer">{t.url}</a>
                    ) : (
                      <span className="small">—</span>
                    )}
                  </td>
                  <td className="small">{fmtDate(t.created_at)}</td>
                  {isAdmin ? (
                    <td>
                      <div className="row" style={{ justifyContent: 'flex-end' }}>
                        <button className="btn secondary" onClick={() => openEdit(t)}>Edit</button>
                        <button className="btn danger" onClick={() => setModal({ mode: 'delete', tool: t })}>Delete</button>
                      </div>
                    </td>
                  ) : null}
                </tr>
              ))}
              {!tools.length ? (
                <tr>
                  <td colSpan={isAdmin ? 7 : 6} className="small">No tools found.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      ) : null}

      {modal?.mode === 'delete' ? (
        <Modal title="Delete Tool" onClose={() => setModal(null)}>
          <div style={{ marginBottom: 12 }}>
            Delete tool <strong>{modal.tool.name}</strong>?
          </div>
          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <button className="btn secondary" onClick={() => setModal(null)}>Cancel</button>
            <button
              className="btn danger"
              onClick={async () => { await remove(modal.tool); setModal(null) }}
            >
              Delete
            </button>
          </div>
        </Modal>
      ) : null}

      {modal && modal.mode !== 'delete' ? (
        <Modal title={modal.mode === 'create' ? 'Create Tool' : 'Edit Tool'} onClose={() => setModal(null)}>
          <div style={{ marginBottom: 10 }}>
            <div className="label">Name</div>
            <input className="input" value={modal.tool.name} onChange={(e) => setModal({ ...modal, tool: { ...modal.tool, name: e.target.value } })} aria-invalid={!!formErrors.name} aria-describedby={formErrors.name ? 'err-name' : undefined} />
            {formErrors.name ? <div id="err-name" style={{ color: '#fca5a5', marginTop: 6 }}>{formErrors.name}</div> : null}
          </div>

          <div style={{ marginBottom: 10 }}>
            <div className="label">Category</div>
            <input className="input" value={modal.tool.category} onChange={(e) => setModal({ ...modal, tool: { ...modal.tool, category: e.target.value } })} placeholder="e.g. ci-cd" aria-invalid={!!formErrors.category} aria-describedby={formErrors.category ? 'err-category' : undefined} />
            {formErrors.category ? <div id="err-category" style={{ color: '#fca5a5', marginTop: 6 }}>{formErrors.category}</div> : null}
          </div>

          <div style={{ marginBottom: 10 }}>
            <div className="label">Tags (comma-separated)</div>
            <input className="input" value={modal.tool.tagsText} onChange={(e) => setModal({ ...modal, tool: { ...modal.tool, tagsText: e.target.value } })} placeholder="e.g. terraform, aws, lint" />
          </div>

          <div style={{ marginBottom: 10 }}>
            <div className="label">Description</div>
            <textarea className="input" rows="3" value={modal.tool.description} onChange={(e) => setModal({ ...modal, tool: { ...modal.tool, description: e.target.value } })} />
            {formErrors.description ? <div style={{ color: '#fca5a5', marginTop: 6 }}>{formErrors.description}</div> : null}
          </div>

          <div style={{ marginBottom: 10 }}>
            <div className="label">URL</div>
            <input className="input" value={modal.tool.url} onChange={(e) => setModal({ ...modal, tool: { ...modal.tool, url: e.target.value } })} aria-invalid={!!formErrors.url} aria-describedby={formErrors.url ? 'err-url' : undefined} />
            {formErrors.url ? <div id="err-url" style={{ color: '#fca5a5', marginTop: 6 }}>{formErrors.url}</div> : null}
          </div>

          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <button className="btn secondary" onClick={() => setModal(null)} disabled={isSaving}>Cancel</button>
            <button className="btn" onClick={save} disabled={isSaving || Object.keys(formErrors).length > 0}>{isSaving ? 'Saving...' : 'Save'}</button>
          </div>
        </Modal>
      ) : null}
    </div>
  )
}
