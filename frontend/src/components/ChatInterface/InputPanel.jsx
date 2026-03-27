import React, { useLayoutEffect, useRef, useState } from 'react';

const InputPanel = ({ onSendMessage, onInterrupt, disabled, isStreaming, isAwaitingStream }) => {
  const [input, setInput] = useState('');
  const textRef = useRef(null);
  const canSend = typeof onSendMessage === 'function';
  const canInterrupt = typeof onInterrupt === 'function';

  useLayoutEffect(() => {
    if (!textRef.current) return;
    textRef.current.style.height = '0px';
    const height = Math.min(textRef.current.scrollHeight, 180);
    textRef.current.style.height = `${height}px`;
  }, [input]);

  const submit = (e) => {
    e.preventDefault();
    if (!input.trim() || disabled || !canSend) return;
    const ok = onSendMessage(input.trim());
    if (ok !== false) setInput('');
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit(e);
    }
  };

  const waiting = isAwaitingStream && !isStreaming;
  const isDisabled = disabled || waiting || (isStreaming && !canInterrupt);

  return (
    <footer className="border-t border-slate-200 bg-white px-3 py-3 sm:px-4">
      <form onSubmit={submit} className="mx-auto flex max-w-4xl items-end gap-2">
        <label htmlFor="chat-input" className="sr-only">
          Message input
        </label>
        <textarea
          ref={textRef}
          id="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={disabled ? 'Connect first to send a message' : 'Ask AutoMentor...'}
          rows={1}
          disabled={isDisabled}
          aria-label="Type your message"
          className="min-h-11 flex-1 resize-none overflow-y-auto rounded-xl border border-slate-300 px-3 py-2 text-sm leading-relaxed outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
        />

        {isStreaming && canInterrupt ? (
          <button
            type="button"
            onClick={onInterrupt}
            className="inline-flex h-11 items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 font-semibold text-red-700 transition hover:bg-red-100"
          >
            <span aria-hidden="true">■</span>
            Stop
          </button>
        ) : (
          <button
            type="submit"
            disabled={disabled || !input.trim() || !canSend || isStreaming || waiting}
            className="h-11 rounded-xl bg-blue-600 px-5 font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
          >
            {waiting ? 'Waiting...' : 'Send'}
          </button>
        )}
      </form>
    </footer>
  );
};

export default InputPanel;
