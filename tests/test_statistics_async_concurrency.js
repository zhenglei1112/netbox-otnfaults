const { test } = require('node:test');
const assert = require('node:assert/strict');

/**
 * 模拟 statistics_dashboard.js 的并发控制与状态机核心机制
 */
function createDashboardAsyncController() {
    let loadDataRequest = 0;
    let faultDetailsRequest = 0;
    let branchDetailsRequest = 0;
    let supervisorDetailsRequest = 0;

    let dataLoadState = 'idle'; // 'idle' | 'loading' | 'success' | 'failed'
    let activeDataSnapshotKey = null;
    let currentDataSnapshotKey = '';

    const loadedDetailTabs = new Set();
    const loadedDetailSnapshots = {
        physical: null,
        branch: null,
        supervisor: null,
    };

    let renderedDashboardPeriod = null;
    let renderedSupervisorDetails = null;
    let activeTabDetailsSnapshot = null;

    let activeTab = 'physical';

    function getFilterSnapshot(year = '2026') {
        return {
            key: `year|${year}-01-01|`,
            year,
            timeParams: `calendar_year=${year}`
        };
    }

    function getFilterSnapshotKey(year) {
        return getFilterSnapshot(year).key;
    }

    // 汇总加载
    async function loadData(fetchSummaryMock, selectedYear) {
        const requestId = ++loadDataRequest;
        const snapshot = getFilterSnapshot(selectedYear);
        dataLoadState = 'loading';

        // 周期切换或刷新时，使所有明细在途请求立即失效，并重置加载状态
        ++faultDetailsRequest;
        ++branchDetailsRequest;
        ++supervisorDetailsRequest;
        loadedDetailTabs.clear();
        loadedDetailSnapshots.physical = null;
        loadedDetailSnapshots.branch = null;
        loadedDetailSnapshots.supervisor = null;

        try {
            const data = await fetchSummaryMock(snapshot);

            // [P1] 乱序竞争保护：若已有更新的汇总请求发出，直接丢弃旧响应
            if (requestId !== loadDataRequest) {
                return;
            }

            dataLoadState = 'success';
            activeDataSnapshotKey = snapshot.key;
            currentDataSnapshotKey = snapshot.key;
            renderedDashboardPeriod = snapshot.year;

            // 透传快照给当前激活 Tab
            loadActiveTabDetails(snapshot);
        } catch (error) {
            if (requestId !== loadDataRequest) {
                return;
            }
            // [P2] 失败时置为 failed 并清除快照，切 Tab 时允许重试
            dataLoadState = 'failed';
            activeDataSnapshotKey = null;
            currentDataSnapshotKey = '';
        }
    }

    function loadActiveTabDetails(snapshot) {
        activeTabDetailsSnapshot = snapshot;
        if (activeTab === 'supervisor') {
            // 触发主管明细
        }
    }

    // 主管明细加载
    async function loadSupervisorDetails(fetchDetailsMock, snapshot) {
        snapshot = snapshot || getFilterSnapshot();
        const snapshotKey = snapshot.key;
        const requestId = ++supervisorDetailsRequest;

        try {
            const data = await fetchDetailsMock(snapshot);
            // [P1 & P2] 校验序号与快照一致性
            if (requestId !== supervisorDetailsRequest || dataLoadState !== 'success' || snapshotKey !== activeDataSnapshotKey) {
                return;
            }
            renderedSupervisorDetails = data.results || [];
            loadedDetailSnapshots.supervisor = snapshotKey;
            loadedDetailTabs.add('supervisor');
        } catch (error) {
            if (requestId !== supervisorDetailsRequest || dataLoadState !== 'success' || snapshotKey !== activeDataSnapshotKey) {
                return;
            }
        }
    }

    // Tab 切换事件
    async function handleTabSwitch(targetTabId, fetchSummaryMock, fetchSupervisorMock, currentSelectedYear) {
        activeTab = targetTabId === 'tab-line-supervisor-btn' ? 'supervisor' : 'physical';
        const snapKey = getFilterSnapshotKey(currentSelectedYear);

        // [P3] 若汇总未成功或筛选快照不匹配，重新拉取汇总数据（切 Tab 允许重试失败请求）
        if (dataLoadState !== 'success' || activeDataSnapshotKey !== snapKey || currentDataSnapshotKey !== snapKey) {
            await loadData(fetchSummaryMock, currentSelectedYear);
        } else {
            // [P2] 汇总已就绪，仅按需拉取当前快照下尚未加载的明细
            if (targetTabId === 'tab-line-supervisor-btn') {
                if (loadedDetailSnapshots.supervisor !== snapKey) {
                    await loadSupervisorDetails(fetchSupervisorMock, getFilterSnapshot(currentSelectedYear));
                }
            }
        }
    }

    return {
        getState: () => ({
            dataLoadState,
            activeDataSnapshotKey,
            currentDataSnapshotKey,
            loadDataRequest,
            supervisorDetailsRequest,
            loadedDetailTabs: Array.from(loadedDetailTabs),
            loadedDetailSnapshots: { ...loadedDetailSnapshots },
            renderedDashboardPeriod,
            renderedSupervisorDetails,
            activeTabDetailsSnapshot,
        }),
        loadData,
        loadSupervisorDetails,
        handleTabSwitch,
        setActiveTab: tab => { activeTab = tab; }
    };
}

test('[P1] loadData 异步乱序：慢返回的旧请求不应覆盖快返回的新请求', async () => {
    const controller = createDashboardAsyncController();

    let resolve2026;
    const promise2026 = new Promise(r => { resolve2026 = r; });
    let resolve2025;
    const promise2025 = new Promise(r => { resolve2025 = r; });

    const fetchMock = async (snapshot) => {
        if (snapshot.year === '2026') return promise2026;
        if (snapshot.year === '2025') return promise2025;
    };

    // 1. 先发起 2026 请求（较慢）
    const p1 = controller.loadData(fetchMock, '2026');
    // 2. 紧接着用户改选 2025，发起 2025 请求（较快）
    const p2 = controller.loadData(fetchMock, '2025');

    // 3. 2025 先返回
    resolve2025({ kpis: {}, year: '2025' });
    await p2;

    let state = controller.getState();
    assert.equal(state.dataLoadState, 'success');
    assert.equal(state.renderedDashboardPeriod, '2025');
    assert.equal(state.activeDataSnapshotKey, 'year|2025-01-01|');
    assert.equal(state.activeTabDetailsSnapshot.year, '2025');

    // 4. 2026 姗姗来迟返回
    resolve2026({ kpis: {}, year: '2026' });
    await p1;

    // 5. 验证 2026 的响应被拦截丢弃，状态和渲染数据严格保持 2025
    state = controller.getState();
    assert.equal(state.dataLoadState, 'success');
    assert.equal(state.renderedDashboardPeriod, '2025');
    assert.equal(state.activeDataSnapshotKey, 'year|2025-01-01|');
    assert.equal(state.activeTabDetailsSnapshot.year, '2025');
});

test('[P1] 日期变更使在途明细请求失效：隐藏 Tab 的旧明细绝不标记为新周期已加载', async () => {
    const controller = createDashboardAsyncController();

    // 先初始化 2026 汇总成功
    await controller.loadData(async () => ({ kpis: {} }), '2026');
    assert.equal(controller.getState().dataLoadState, 'success');

    // 用户在主管 Tab 发起 2026 主管明细（慢请求）
    let resolveSupervisor2026;
    const supervisorPromise2026 = new Promise(r => { resolveSupervisor2026 = r; });
    const supervisorRequestPromise = controller.loadSupervisorDetails(
        () => supervisorPromise2026,
        { key: 'year|2026-01-01|', year: '2026' }
    );

    // 在主管明细在途期间，用户切换到物理页并改选 2025 发起汇总
    await controller.loadData(async () => ({ kpis: {} }), '2025');

    const stateAfterSummary = controller.getState();
    assert.equal(stateAfterSummary.activeDataSnapshotKey, 'year|2025-01-01|');
    assert.equal(stateAfterSummary.loadedDetailSnapshots.supervisor, null);

    // 此时旧的 2026 主管明细终于返回
    resolveSupervisor2026({ results: [{ id: 999, name: 'old_supervisor_fault' }] });
    await supervisorRequestPromise;

    // 验证：旧主管响应被丢弃，loadedDetailSnapshots.supervisor 依然为 null，且未保存旧数据
    const finalState = controller.getState();
    assert.equal(finalState.loadedDetailSnapshots.supervisor, null);
    assert.equal(finalState.loadedDetailTabs.includes('supervisor'), false);
    assert.equal(finalState.renderedSupervisorDetails, null);
});

test('[P2] 汇总失败后切 Tab 能够重新尝试加载', async () => {
    const controller = createDashboardAsyncController();

    let attempts = 0;
    const fetchMock = async () => {
        attempts++;
        if (attempts === 1) {
            throw new Error('500 Server Error');
        }
        return { kpis: {}, year: '2026' };
    };

    // 1. 发起汇总，返回失败
    await controller.loadData(fetchMock, '2026');

    let state = controller.getState();
    assert.equal(state.dataLoadState, 'failed');
    assert.equal(state.activeDataSnapshotKey, null);
    assert.equal(state.currentDataSnapshotKey, '');

    // 2. 用户切换 Tab（例如切到主管 Tab），应因 dataLoadState !== 'success' 触发重试 loadData
    let supervisorLoaded = false;
    const supervisorMock = async () => {
        supervisorLoaded = true;
        return { results: [] };
    };

    await controller.handleTabSwitch('tab-line-supervisor-btn', fetchMock, supervisorMock, '2026');

    state = controller.getState();
    assert.equal(attempts, 2, '应触发第 2 次 loadData 重试');
    assert.equal(state.dataLoadState, 'success', '重试成功后状态为 success');
    assert.equal(state.activeDataSnapshotKey, 'year|2026-01-01|');
    assert.equal(state.currentDataSnapshotKey, 'year|2026-01-01|');

    // 3. 汇总就绪后再切回物理 Tab，不应再次触发 loadData
    await controller.handleTabSwitch('tab-physical-btn', fetchMock, supervisorMock, '2026');
    assert.equal(attempts, 2, '汇总成功后切 Tab 应复用汇总数据，不再调用 loadData');
});
