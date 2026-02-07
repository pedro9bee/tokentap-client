/**
 * Alpine.js app for tokentap dashboard.
 */
document.addEventListener('alpine:init', () => {

  Alpine.data('dashboard', () => ({
    // State
    tab: 'overview',
    summary: { total_input_tokens: 0, total_output_tokens: 0, request_count: 0, total_cache_creation_tokens: 0, total_cache_read_tokens: 0 },
    byModel: [],
    overTime: [],
    events: [],
    eventsTotal: 0,
    eventsPage: 0,
    eventsLimit: 25,
    selectedEvent: null,
    loading: true,
    error: null,

    // Filters
    filterProvider: '',
    filterModel: '',
    filterDateFrom: '',
    filterDateTo: '',
    granularity: 'hour',

    get filterParams() {
      return {
        provider: this.filterProvider,
        model: this.filterModel,
        date_from: this.filterDateFrom,
        date_to: this.filterDateTo,
      };
    },

    get totalTokens() {
      return this.summary.total_input_tokens + this.summary.total_output_tokens;
    },

    get avgTokens() {
      if (!this.summary.request_count) return 0;
      return Math.round(this.totalTokens / this.summary.request_count);
    },

    get totalPages() {
      return Math.ceil(this.eventsTotal / this.eventsLimit);
    },

    async init() {
      await this.refresh();
      // Auto-refresh every 10 seconds
      setInterval(() => this.refresh(), 10000);
    },

    async refresh() {
      this.loading = true;
      this.error = null;
      try {
        await Promise.all([
          this.loadSummary(),
          this.loadByModel(),
          this.loadOverTime(),
          this.loadEvents(),
        ]);
      } catch (e) {
        this.error = e.message;
      }
      this.loading = false;
    },

    async applyFilters() {
      this.eventsPage = 0;
      await this.refresh();
    },

    async clearFilters() {
      this.filterProvider = '';
      this.filterModel = '';
      this.filterDateFrom = '';
      this.filterDateTo = '';
      this.eventsPage = 0;
      await this.refresh();
    },

    async loadSummary() {
      this.summary = await API.getSummary(this.filterParams);
    },

    async loadByModel() {
      this.byModel = await API.getByModel(this.filterParams);
    },

    async loadOverTime() {
      const data = await API.getOverTime({ ...this.filterParams, granularity: this.granularity });
      this.overTime = data;
      this.$nextTick(() => createUsageChart('usageChart', data));
    },

    async loadEvents() {
      const data = await API.getEvents({
        ...this.filterParams,
        skip: this.eventsPage * this.eventsLimit,
        limit: this.eventsLimit,
      });
      this.events = data.events;
      this.eventsTotal = data.total;
    },

    async prevPage() {
      if (this.eventsPage > 0) {
        this.eventsPage--;
        await this.loadEvents();
      }
    },

    async nextPage() {
      if (this.eventsPage < this.totalPages - 1) {
        this.eventsPage++;
        await this.loadEvents();
      }
    },

    async showEventDetail(id) {
      this.selectedEvent = await API.getEvent(id);
    },

    closeDetail() {
      this.selectedEvent = null;
    },

    async changeGranularity(g) {
      this.granularity = g;
      await this.loadOverTime();
    },

    formatNumber(n) {
      if (n === null || n === undefined) return '0';
      return Number(n).toLocaleString();
    },

    formatTime(iso) {
      if (!iso) return '';
      const d = new Date(iso);
      return d.toLocaleString();
    },

    shortModel(model) {
      if (!model) return 'unknown';
      // Shorten long model names
      if (model.length > 30) return model.substring(0, 27) + '...';
      return model;
    },
  }));
});
