/**
 * 搜索控件 (SearchControl)
 * 实现类似高德地图的搜索功能：
 * 1. 搜索站点和路径
 * 2. 显示匹配结果（图标、名称、省份）
 * 3. 点击结果 fly to 并弹出标签
 */
class SearchControl {
    constructor(options) {
        this.options = options || {};
        this.container = null;
        this.input = null;
        this.resultList = null;
        this.isOpen = false;
        this.debounceTimer = null;
    }

    onAdd(map) {
        this.map = map;
        this.container = document.createElement('div');
        this.container.className = 'maplibregl-ctrl search-control';
        
        this.createSearchBox();
        
        // 阻止地图事件传播
        ['mousedown', 'click', 'dblclick', 'touchstart'].forEach(event => {
            this.container.addEventListener(event, e => e.stopPropagation());
        });

        // 点击外部关闭结果列表
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.hideResults();
            }
        });

        return this.container;
    }

    onRemove() {
        this.container.parentNode.removeChild(this.container);
        this.map = undefined;
    }

    createSearchBox() {
        // 搜索框容器
        const wrapper = document.createElement('div');
        wrapper.className = 'search-wrapper';
        
        // 搜索图标
        const icon = document.createElement('span');
        icon.className = 'search-icon';
        icon.innerHTML = '<i class="mdi mdi-magnify"></i>';
        
        // 输入框
        this.input = document.createElement('input');
        this.input.type = 'text';
        this.input.className = 'search-input';
        this.input.placeholder = '搜索站点或路径...';
        
        // 清除按钮
        const clearBtn = document.createElement('span');
        clearBtn.className = 'search-clear';
        clearBtn.innerHTML = '<i class="mdi mdi-close"></i>';
        clearBtn.style.display = 'none';
        clearBtn.onclick = () => {
            this.input.value = '';
            clearBtn.style.display = 'none';
            this.hideResults();
        };
        
        // 输入事件（防抖）
        this.input.oninput = () => {
            const value = this.input.value.trim();
            clearBtn.style.display = value ? 'flex' : 'none';
            
            clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(() => {
                this.performSearch(value);
            }, 100); // 更快的实时响应
        };
        
        // 聚焦时如果有内容则显示结果
        this.input.onfocus = () => {
            const value = this.input.value.trim();
            if (value) {
                this.performSearch(value);
            }
        };
        
        wrapper.appendChild(icon);
        wrapper.appendChild(this.input);
        wrapper.appendChild(clearBtn);
        this.clearBtn = clearBtn;
        
        // 结果列表容器
        this.resultList = document.createElement('div');
        this.resultList.className = 'search-results';
        this.resultList.style.display = 'none';
        
        this.container.appendChild(wrapper);
        this.container.appendChild(this.resultList);
    }

    /**
     * 执行搜索
     */
    performSearch(query) {
        if (!query) {
            this.hideResults();
            return;
        }
        
        const results = this.search(query);
        this.renderResults(results, query);
    }

    /**
     * 搜索站点和路径
     */
    search(query) {
        const siteResults = [];
        const pathResults = [];
        const lowerQuery = query.toLowerCase();
        
        // 搜索站点
        const sites = window.OTNFaultMapConfig?.sitesData || [];
        sites.forEach(site => {
            const nameMatch = site.name?.toLowerCase().includes(lowerQuery);
            const regionMatch = site.region?.toLowerCase().includes(lowerQuery);
            
            if (nameMatch || regionMatch) {
                siteResults.push({
                    type: 'site',
                    id: site.id,
                    name: site.name,
                    region: site.region || '',
                    longitude: site.longitude,
                    latitude: site.latitude,
                    // 名称匹配优先级更高
                    priority: nameMatch ? 1 : 2
                });
            }
        });
        
        // 搜索路径（使用路径模型的name字段）
        const paths = window.OTNPathsMetadata || [];
        paths.forEach(path => {
            const props = path.properties || {};
            const pathName = props.name || '';
            const aSite = props.a_site || '';
            const zSite = props.z_site || '';
            
            // 用路径名称进行模糊搜索
            const nameMatch = pathName.toLowerCase().includes(lowerQuery);
            const aSiteMatch = aSite.toLowerCase().includes(lowerQuery);
            const zSiteMatch = zSite.toLowerCase().includes(lowerQuery);
            
            if (nameMatch || aSiteMatch || zSiteMatch) {
                // 计算路径中心点
                let center = null;
                if (path.geometry && path.geometry.coordinates) {
                    const coords = path.geometry.coordinates;
                    if (coords.length > 0) {
                        const midIndex = Math.floor(coords.length / 2);
                        center = coords[midIndex];
                    }
                }
                
                pathResults.push({
                    type: 'path',
                    name: pathName || `${aSite} ↔ ${zSite}`,
                    aSite: aSite,
                    zSite: zSite,
                    center: center,
                    // 名称匹配优先级更高
                    priority: nameMatch ? 1 : 2
                });
            }
        });
        
        // 分别排序
        const sortFn = (a, b) => {
            if (a.priority !== b.priority) {
                return a.priority - b.priority;
            }
            return a.name.localeCompare(b.name);
        };
        
        siteResults.sort(sortFn);
        pathResults.sort(sortFn);
        
        // 返回所有匹配结果（站点优先）
        return [...siteResults, ...pathResults];
    }

    /**
     * 渲染搜索结果（分组显示）
     */
    renderResults(results, query) {
        if (results.length === 0) {
            this.resultList.innerHTML = `
                <div class="search-no-result">
                    <i class="mdi mdi-magnify-close"></i>
                    <span>无匹配结果</span>
                </div>
            `;
            this.resultList.style.display = 'block';
            return;
        }
        
        // 分组渲染
        const siteResults = results.filter(r => r.type === 'site');
        const pathResults = results.filter(r => r.type === 'path');
        
        let html = '';
        
        // 站点分组
        if (siteResults.length > 0) {
            html += `<div class="search-group-header site-group"><i class="mdi mdi-map-marker"></i>站点 (${siteResults.length})</div>`;
            html += siteResults.map(item => this.renderSiteItem(item, query)).join('');
        }
        
        // 路径分组
        if (pathResults.length > 0) {
            html += `<div class="search-group-header path-group"><i class="mdi mdi-vector-polyline"></i>路径 (${pathResults.length})</div>`;
            html += pathResults.map(item => this.renderPathItem(item, query)).join('');
        }
        
        this.resultList.innerHTML = html;
        this.resultList.style.display = 'block';
        
        // 绑定点击事件（分组后需要重新计算索引）
        const allItems = [...siteResults, ...pathResults];
        this.resultList.querySelectorAll('.search-result-item').forEach((el, index) => {
            el.onclick = () => {
                const item = allItems[index];
                this.onResultClick(item);
            };
        });
    }

    /**
     * 渲染站点搜索结果项（省份与名称同行）
     */
    renderSiteItem(item, query) {
        const highlightedName = this.highlightMatch(item.name, query);
        const regionText = item.region ? ` · ${item.region}` : '';
        
        return `
            <div class="search-result-item" data-type="site">
                <div class="search-result-icon site-icon">
                    <i class="mdi mdi-map-marker"></i>
                </div>
                <div class="search-result-content">
                    <div class="search-result-name">${highlightedName}<span class="search-result-region">${regionText}</span></div>
                </div>
            </div>
        `;
    }

    /**
     * 渲染路径搜索结果项（不显示副标题）
     */
    renderPathItem(item, query) {
        const highlightedName = this.highlightMatch(item.name, query);
        
        return `
            <div class="search-result-item" data-type="path">
                <div class="search-result-icon path-icon">
                    <i class="mdi mdi-vector-polyline"></i>
                </div>
                <div class="search-result-content">
                    <div class="search-result-name">${highlightedName}</div>
                </div>
            </div>
        `;
    }

    /**
     * 高亮匹配文字
     */
    highlightMatch(text, query) {
        if (!text || !query) return text || '';
        
        const lowerText = text.toLowerCase();
        const lowerQuery = query.toLowerCase();
        const index = lowerText.indexOf(lowerQuery);
        
        if (index === -1) return text;
        
        const before = text.slice(0, index);
        const match = text.slice(index, index + query.length);
        const after = text.slice(index + query.length);
        
        return `${before}<span class="search-highlight">${match}</span>${after}`;
    }

    /**
     * 点击搜索结果
     */
    onResultClick(item) {
        this.hideResults();
        this.input.blur();
        
        // 清除之前的高亮线路
        if (this.map && this.map.getSource('otn-paths-highlight')) {
            this.map.getSource('otn-paths-highlight').setData({
                type: 'Feature',
                geometry: { type: 'LineString', coordinates: [] }
            });
        }
        
        if (item.type === 'site') {
            // 使用 FaultStatisticsControl 的 flyToSite 方法
            if (window.faultStatisticsControl && window.faultStatisticsControl.flyToSite) {
                window.faultStatisticsControl.flyToSite(item.name);
            } else {
                // fallback: 直接 fly to
                this.map.flyTo({
                    center: [item.longitude, item.latitude],
                    zoom: 12,
                    speed: 2.5
                });
            }
        } else if (item.type === 'path') {
            // 构建路径名称格式 "A <-> Z"
            const pathName = `${item.aSite} <-> ${item.zSite}`;
            
            // 使用 FaultStatisticsControl 的 flyToPath 方法
            if (window.faultStatisticsControl && window.faultStatisticsControl.flyToPath) {
                window.faultStatisticsControl.flyToPath(pathName);
            } else if (item.center) {
                // fallback: 直接 fly to 中心点
                this.map.flyTo({
                    center: item.center,
                    zoom: 8,
                    speed: 2.5
                });
            }
        }
    }

    /**
     * 隐藏搜索结果
     */
    hideResults() {
        this.resultList.style.display = 'none';
    }
}
