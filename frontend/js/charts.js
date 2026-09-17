// Chart.js helper functions with minimalist Linear/Vercel styling
const chartInstances = {};

export const charts = {
  destroy(canvasId) {
    if (chartInstances[canvasId]) {
      chartInstances[canvasId].destroy();
      delete chartInstances[canvasId];
    }
  },

  getThemeColors() {
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    return {
      textColor: isLight ? '#71717a' : '#71717a',
      gridColor: isLight ? 'rgba(0, 0, 0, 0.04)' : 'rgba(255, 255, 255, 0.04)',
      donutBorder: isLight ? '#ffffff' : '#121215',
      tooltipBg: isLight ? '#ffffff' : '#18181b',
      tooltipBorder: isLight ? '#e4e4e7' : '#27272a',
      tooltipText: isLight ? '#09090b' : '#f4f4f5',
    };
  },

  renderLine(canvasId, labels, data, label = 'Metric', color = '#2563eb') {
    this.destroy(canvasId);
    if (typeof Chart === 'undefined') return;
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    const theme = this.getThemeColors();

    try {
      chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: label,
            data: data,
            borderColor: color,
            backgroundColor: 'rgba(37, 99, 235, 0.04)',
            fill: true,
            tension: 0.2,
            borderWidth: 1.5,
            pointRadius: 2.5,
            pointHoverRadius: 4.5,
            pointBackgroundColor: color,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { 
              display: false,
            },
            tooltip: { 
              padding: 8, 
              cornerRadius: 6,
              backgroundColor: theme.tooltipBg,
              borderColor: theme.tooltipBorder,
              borderWidth: 1,
              titleColor: theme.tooltipText,
              bodyColor: theme.tooltipText,
              displayColors: false,
              titleFont: { family: 'Inter', size: 11, weight: '500' },
              bodyFont: { family: 'Inter', size: 12, weight: '600' },
            },
          },
          scales: {
            x: { 
              grid: { color: theme.gridColor, drawBorder: false }, 
              ticks: { color: theme.textColor, font: { family: 'Inter', size: 10 } } 
            },
            y: { 
              grid: { color: theme.gridColor, drawBorder: false }, 
              ticks: { color: theme.textColor, font: { family: 'Inter', size: 10 } } 
            },
          },
        },
      });
    } catch (e) {
      console.warn('renderLine error:', e);
    }
  },

  renderBar(canvasId, labels, data, label = 'Count', color = '#2563eb') {
    this.destroy(canvasId);
    if (typeof Chart === 'undefined') return;
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    const theme = this.getThemeColors();

    try {
      chartInstances[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: label,
            data: data,
            backgroundColor: color,
            borderRadius: 4,
            borderSkipped: false,
            maxBarThickness: 32,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { 
              padding: 8, 
              cornerRadius: 6,
              backgroundColor: theme.tooltipBg,
              borderColor: theme.tooltipBorder,
              borderWidth: 1,
              titleColor: theme.tooltipText,
              bodyColor: theme.tooltipText,
              displayColors: false,
              titleFont: { family: 'Inter', size: 11, weight: '500' },
              bodyFont: { family: 'Inter', size: 12, weight: '600' },
            },
          },
          scales: {
            x: { 
              grid: { display: false }, 
              ticks: { color: theme.textColor, font: { family: 'Inter', size: 10 } } 
            },
            y: { 
              grid: { color: theme.gridColor, drawBorder: false }, 
              ticks: { color: theme.textColor, font: { family: 'Inter', size: 10 } } 
            },
          },
        },
      });
    } catch (e) {
      console.warn('renderBar error:', e);
    }
  },

  renderDonut(canvasId, labels, data, colors = ['#10b981', '#2563eb', '#f59e0b', '#ef4444']) {
    this.destroy(canvasId);
    if (typeof Chart === 'undefined') return;
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    const theme = this.getThemeColors();

    try {
      chartInstances[canvasId] = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: data,
            backgroundColor: colors,
            borderWidth: 1,
            borderColor: theme.donutBorder,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '76%',
          plugins: {
            legend: { 
              position: 'bottom', 
              labels: { 
                color: theme.textColor, 
                boxWidth: 8, 
                boxHeight: 8,
                borderRadius: 2,
                useBorderRadius: true,
                padding: 12,
                font: { family: 'Inter', size: 11 } 
              } 
            },
            tooltip: { 
              padding: 8, 
              cornerRadius: 6,
              backgroundColor: theme.tooltipBg,
              borderColor: theme.tooltipBorder,
              borderWidth: 1,
              titleColor: theme.tooltipText,
              bodyColor: theme.tooltipText,
              titleFont: { family: 'Inter', size: 11 },
              bodyFont: { family: 'Inter', size: 12 },
            },
          },
        },
      });
    } catch (e) {
      console.warn('renderDonut error:', e);
    }
  },

  renderScatter(canvasId, points, label = 'Observations', color = '#2563eb') {
    this.destroy(canvasId);
    if (typeof Chart === 'undefined') return;
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    const theme = this.getThemeColors();

    try {
      chartInstances[canvasId] = new Chart(ctx, {
        type: 'scatter',
        data: {
          datasets: [{
            label: label,
            data: points,
            backgroundColor: color,
            pointRadius: 3.5,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { 
              padding: 8, 
              cornerRadius: 6,
              backgroundColor: theme.tooltipBg,
              borderColor: theme.tooltipBorder,
              borderWidth: 1,
              titleColor: theme.tooltipText,
              bodyColor: theme.tooltipText,
            },
          },
          scales: {
            x: { grid: { color: theme.gridColor, drawBorder: false }, ticks: { color: theme.textColor, font: { size: 10 } } },
            y: { grid: { color: theme.gridColor, drawBorder: false }, ticks: { color: theme.textColor, font: { size: 10 } } },
          },
        },
      });
    } catch (e) {
      console.warn('renderScatter error:', e);
    }
  },
};
