function normalizeCount(value) {
  const count = Number(value);
  return Number.isFinite(count) && count >= 0 ? count : 0;
}

function stableSerialize(value) {
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableSerialize(item)).join(',')}]`;
  }
  if (value && typeof value === 'object') {
    const entries = Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableSerialize(value[key])}`);
    return `{${entries.join(',')}}`;
  }
  return JSON.stringify(value);
}

export function createDashboardV2RenderSignature(data) {
  const processingFaults = Array.isArray(data?.processing_faults)
    ? data.processing_faults
    : [];
  const faultSignatures = processingFaults.map((fault) => {
    if (!fault || typeof fault !== 'object' || Array.isArray(fault)) {
      return stableSerialize(fault);
    }
    const {
      duration: _duration,
      priority_score: _priorityScore,
      ...stableFault
    } = fault;
    return stableSerialize(stableFault);
  }).sort();
  const siteSignatures = (Array.isArray(data?.sites) ? data.sites : [])
    .map((site) => stableSerialize(site))
    .sort();

  return stableSerialize({
    processing_faults: faultSignatures,
    sites: siteSignatures,
    summary: data?.summary && typeof data.summary === 'object' ? data.summary : {},
  });
}

export async function fetchDashboardV2Data(dataUrl) {
  if (!dataUrl) {
    throw new Error('未配置态势数据地址');
  }

  const response = await fetch(dataUrl, {
    credentials: 'same-origin',
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
  });
  if (!response.ok) {
    throw new Error(`态势数据请求失败（HTTP ${response.status}）`);
  }

  const data = await response.json();
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error('态势数据格式无效');
  }

  const rawSummary = data.summary && typeof data.summary === 'object'
    ? data.summary
    : {};
  return {
    timestamp: typeof data.timestamp === 'string' ? data.timestamp : '',
    summary: {
      total_faults: normalizeCount(rawSummary.total_faults),
      processing_faults: normalizeCount(rawSummary.processing_faults),
      today_faults: normalizeCount(rawSummary.today_faults),
      active_business_interruptions: normalizeCount(
        rawSummary.active_business_interruptions,
      ),
    },
    processing_faults: Array.isArray(data.processing_faults) ? data.processing_faults : [],
    sites: Array.isArray(data.sites) ? data.sites : [],
  };
}

export async function fetchDashboardV2Sites(dataUrl) {
  const data = await fetchDashboardV2Data(dataUrl);
  return data.sites;
}
