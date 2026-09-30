import React from 'react';
import { MemoryList } from './MemoryPrompt';
import Overlay from './Overlay';
import PersonalityPanel from './PersonalityPanel';

export default function ParametersOverlay({ onClose, memoryRefresh }) {
  return (
    <Overlay title="Parameters" onClose={onClose}>
      <PersonalityPanel defaultOpen />
      <MemoryList refreshKey={memoryRefresh} defaultOpen />
    </Overlay>
  );
}
