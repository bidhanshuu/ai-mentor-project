# AutoMentor Frontend

## Required Environment Variables

Create `.env` in `frontend/`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_WS_BASE_URL=ws://127.0.0.1:8000
```

## Run Commands

```bash
npm install
npm run dev
```

## Production Build

```bash
npm run build
npm run preview
```

## WebSocket Contract (Expected JSON)

Server -> Client envelope:

```json
{
  "event": "connection_established | agent_state_update | message_chunk | ui_component_trigger | request_complete | error",
  "data": {}
}
```

`message_chunk`:

```json
{
  "event": "message_chunk",
  "data": {
    "sender": "assistant",
    "chunk": "partial text",
    "is_final": false
  }
}
```

`ui_component_trigger`:

```json
{
  "event": "ui_component_trigger",
  "data": {
    "component_type": "readiness_badge | calendar_widget | quiz_widget | resource_card | progress_tracker",
    "action": "render",
    "payload": {}
  }
}
```

Client -> Server `user_message`:

```json
{
  "event": "user_message",
  "data": {
    "content": "hello",
    "session_id": "session-id"
  }
}
```
