import React, { useEffect, useRef } from 'react'

export default function Modal({ title, children, onClose }) {
  const rootRef = useRef(null)
  const previouslyFocused = useRef(null)

  useEffect(() => {
    // Save previously focused element to restore on close
    previouslyFocused.current = document.activeElement

    // Focus first focusable element inside the modal, or the modal itself
    const root = rootRef.current
    if (root) {
      const focusable = root.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
      if (focusable.length) {
        focusable[0].focus()
      } else {
        root.focus()
      }
    }

    function onKeyDown(e) {
      if (e.key === 'Escape') {
        onClose()
      }
      // Simple focus trap: keep focus within modal on Tab
      if (e.key === 'Tab' && root) {
        const focusableEls = Array.from(root.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'))
          .filter((el) => !el.hasAttribute('disabled'))
        if (focusableEls.length === 0) return
        const first = focusableEls[0]
        const last = focusableEls[focusableEls.length - 1]
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      // restore focus
      try { previouslyFocused.current?.focus() } catch (e) {}
    }
  }, [onClose])

  return (
    <div className="modalBackdrop" onMouseDown={onClose} role="presentation">
      <div
        className="card modal"
        ref={rootRef}
        onMouseDown={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
      >
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <div id="modal-title" style={{ fontWeight: 700 }}>{title}</div>
          <button className="btn secondary" onClick={onClose}>Close</button>
        </div>
        <div style={{ marginTop: 12 }}>
          {children}
        </div>
      </div>
    </div>
  )
}
