/**
 * API client for tokentap dashboard.
 */
const API = {
  async fetchJSON(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    return resp.json();
  },

  async getEvents(params = {}) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== null && v !== undefined && v !== '') qs.set(k, v);
    }
    return this.fetchJSON(`/api/events?${qs}`);
  },

  async getEvent(id) {
    return this.fetchJSON(`/api/events/${id}`);
  },

  async getSummary(params = {}) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== null && v !== undefined && v !== '') qs.set(k, v);
    }
    return this.fetchJSON(`/api/stats/summary?${qs}`);
  },

  async getByModel(params = {}) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== null && v !== undefined && v !== '') qs.set(k, v);
    }
    return this.fetchJSON(`/api/stats/by-model?${qs}`);
  },

  async getOverTime(params = {}) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== null && v !== undefined && v !== '') qs.set(k, v);
    }
    return this.fetchJSON(`/api/stats/over-time?${qs}`);
  },

  async getHealth() {
    return this.fetchJSON('/api/health');
  },

  async deleteAllEvents() {
    const resp = await fetch('/api/events/all', { method: 'DELETE' });
    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    return resp.json();
  },

  // Device management (v0.5.0)
  async getDevices() {
    return this.fetchJSON('/api/devices');
  },

  async getDeviceStats(params = {}) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== null && v !== undefined && v !== '') qs.set(k, v);
    }
    return this.fetchJSON(`/api/stats/by-device?${qs}`);
  },

  async renameDevice(deviceId, name) {
    const resp = await fetch(`/api/devices/${deviceId}/rename`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    return resp.json();
  },

  async deleteDevice(deviceId) {
    const resp = await fetch(`/api/devices/${deviceId}`, {
      method: 'DELETE'
    });
    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    return resp.json();
  }
};
