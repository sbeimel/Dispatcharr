// src/components/Dashboard.js
import React, { useState } from 'react';

const Dashboard = () => {
  const [newStream, setNewStream] = useState('');

  return (
    <div>
      <h1>Dashboard Page</h1>
      <input
        type="text"
        value={newStream}
        onChange={(e) => setNewStream(e.target.value)}
        placeholder="Enter Stream"
      />

      <h3>Streams:</h3>
      <ul>
        {state.streams.map((stream, index) => (
          <li key={index}>{stream}</li>
        ))}
      </ul>
    </div>
  );
};

export default Dashboard;
