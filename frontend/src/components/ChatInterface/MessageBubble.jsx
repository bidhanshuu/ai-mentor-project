import React from 'react';
import PayloadRouter from '../PayloadRenderers/PayloadRouter';

const MessageBubble = ({ message }) => {
  if (!message) return null;

  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const trigger = message.meta?.trigger || message.metadata?.trigger || null;
  const senderLabel = message.meta?.sender || message.metadata?.sender || null;
  const ts = message.createdAt || message.timestamp || Date.now();

  if (isSystem) {
    return (
      <li className="my-3 flex justify-center">
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
          {message.content}
        </span>
      </li>
    );
  }

  return (
    <li className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}>
      <article
        className={`max-w-[85%] rounded-2xl px-3 py-2 shadow-sm sm:max-w-[80%] ${
          isUser
            ? 'rounded-tr-md bg-blue-600 text-white'
            : 'rounded-tl-md border border-slate-200 bg-white text-slate-800'
        }`}
      >
        {!isUser && senderLabel ? (
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            {senderLabel}
          </p>
        ) : null}

        {message.content ? (
          <p className="mb-2 whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
        ) : null}

        {trigger ? (
          <section className="mt-2 border-t border-slate-100 pt-2">
            <PayloadRouter trigger={trigger} />
          </section>
        ) : null}

        <time
          className={`mt-1 block text-[10px] ${isUser ? 'text-blue-100' : 'text-slate-400'}`}
          dateTime={new Date(ts).toISOString()}
        >
          {new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </time>
      </article>
    </li>
  );
};

export default MessageBubble;
