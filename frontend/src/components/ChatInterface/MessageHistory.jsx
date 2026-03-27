import React, { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';

const MessageHistory = ({ messages = [], streamingMessage = null }) => {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  const isEmpty = messages.length === 0 && !streamingMessage;

  return (
    <section className="flex flex-1 flex-col overflow-y-auto bg-slate-50 p-3 sm:p-4">
      <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-2">
        {isEmpty ? (
          <aside className="flex min-h-72 flex-1 flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white px-6 text-center">
            <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-sm font-semibold text-slate-600">
              AM
            </div>
            <h2 className="text-lg font-semibold text-slate-800 sm:text-xl">AutoMentor</h2>
            <p className="mt-1 max-w-md text-sm text-slate-500">
              Start a conversation to get guided explanations, study plans, and targeted practice.
            </p>
          </aside>
        ) : (
          <ul className="flex flex-col gap-2" aria-live="polite">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {streamingMessage ? (
              <li className="opacity-90 transition-opacity duration-150 ease-in">
                <MessageBubble message={streamingMessage} />
              </li>
            ) : null}
          </ul>
        )}
        <div ref={bottomRef} className="h-2" />
      </div>
    </section>
  );
};

export default React.memo(MessageHistory);
