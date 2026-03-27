import React from 'react';
import { PAYLOAD_TYPES } from '../../types/messages';
import { isSupportedPayloadType, validatePayloadTrigger } from '../../utils/validators';
import ReadinessBadge from './ReadinessBadge';
import CalendarWidget from './CalendarWidget';
import GenericPayload from './GenericPayload';

const strategies = {
  [PAYLOAD_TYPES.READINESS]: (trigger) => <ReadinessBadge data={trigger.payload} />,
  [PAYLOAD_TYPES.CALENDAR]: (trigger) => <CalendarWidget data={trigger.payload} />,
};

const PayloadRouter = ({ trigger }) => {
  const validation = validatePayloadTrigger(trigger);
  if (!validation.ok) {
    return <GenericPayload trigger={trigger} reason={validation.error} />;
  }
  if (!isSupportedPayloadType(trigger.type)) {
    return <GenericPayload trigger={trigger} reason="Unsupported payload type" />;
  }
  const render = strategies[trigger.type];
  return render ? render(trigger) : <GenericPayload trigger={trigger} reason="No renderer found" />;
};

export default PayloadRouter;
