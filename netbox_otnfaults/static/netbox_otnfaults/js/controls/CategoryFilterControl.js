
// 故障类型颜色（用于仅需要类型区分的场景，如筛选器）
const FAULT_CATEGORY_COLORS = {
    'power': '#ff0000',    // 红色
    'fiber': '#ffa500',    // 橙色
    'pigtail': '#ffff00',  // 黄色
    'device': '#800080',   // 紫色
    'other': '#808080'     // 灰色
};

const FAULT_CATEGORY_NAMES = {
    'power': '电力故障', 'fiber': '光缆故障', 'pigtail': '空调故障', 'device': '设备故障', 'other': '其他故障'
};

// 故障状态颜色（与 models.py 中 FaultStatusChoices 对应）
const FAULT_STATUS_COLORS = {
    'processing': '#dc3545',       // 处理中 - 红色
    'temporary_recovery': '#0d6efd', // 临时恢复 - 蓝色
    'suspended': '#ffc107',        // 挂起 - 黄色
    'closed': '#198754'            // 已关闭 - 绿色
};

const FAULT_STATUS_NAMES = {
    'processing': '处理中',
    'temporary_recovery': '临时恢复',
    'suspended': '挂起',
    'closed': '已关闭'
};

// 挂载到 window 对象，确保全局可访问
window.FAULT_CATEGORY_COLORS = FAULT_CATEGORY_COLORS;
window.FAULT_CATEGORY_NAMES = FAULT_CATEGORY_NAMES;
window.FAULT_STATUS_COLORS = FAULT_STATUS_COLORS;
window.FAULT_STATUS_NAMES = FAULT_STATUS_NAMES;


/**
 * 故障分类筛选控件 (下拉菜单式)
 */
class CategoryFilterControl {
    constructor() {
        this.selectedCategories = Object.keys(FAULT_CATEGORY_COLORS);
        this.menuHovered = false;
        
        // 跟踪鼠标位置以实现更智能的菜单关闭
        document.addEventListener('mousemove', (e) => {
             this.lastMouseX = e.clientX;
             this.lastMouseY = e.clientY;
        });
    }

    onAdd(map) {
        this.map = map;
        this.container = document.createElement('div');
        this.container.className = 'maplibregl-ctrl maplibregl-ctrl-group category-filter-control';

        // 按钮
        this.button = document.createElement('button');
        this.button.className = 'maplibregl-ctrl-icon';
        this.button.innerHTML = window.mapBase.svgIcons.network; // 使用网络图标或其他合适的图标
        this.button.title = '故障分类筛选';
        
        // 菜单容器 (绝对定位)
        this.menu = document.createElement('div');
        this.menu.className = 'dropdown-menu category-filter-menu';
        this.menu.style.display = 'none';
        this.menu.style.position = 'absolute';
        this.menu.style.right = '40px'; // 按钮右侧向左弹出 或 left: 40px
        this.menu.style.top = '0';
        this.menu.style.minWidth = '150px';
        
        // 生成菜单项
        Object.keys(FAULT_CATEGORY_COLORS).forEach(cat => {
            const item = document.createElement('label');
            item.className = 'dropdown-item d-flex align-items-center gap-2';
            item.style.cursor = 'pointer';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = true;
            checkbox.className = 'form-check-input mt-0';
            checkbox.dataset.category = cat;
            
            const colorBox = document.createElement('span');
            colorBox.style.width = '12px';
            colorBox.style.height = '12px';
            colorBox.style.backgroundColor = FAULT_CATEGORY_COLORS[cat];
            colorBox.style.borderRadius = '50%';
            colorBox.style.display = 'inline-block';

            const text = document.createElement('span');
            text.innerText = FAULT_CATEGORY_NAMES[cat];
            
            item.appendChild(checkbox);
            item.appendChild(colorBox);
            item.appendChild(text);

            item.onclick = (e) => {
                // 阻止菜单关闭
                e.stopPropagation();
                
                // 如果点击的不是 checkbox 本身（点击了 label），手动切换 checked
                if (e.target !== checkbox) {
                    checkbox.checked = !checkbox.checked;
                }
                
                this.toggleCategory(cat, checkbox.checked);
            };

            this.menu.appendChild(item);
        });

        // 顶部“全选”
        const allItem = document.createElement('label');
        allItem.className = 'dropdown-item d-flex align-items-center gap-2 border-bottom mb-1 pb-1';
        allItem.style.cursor = 'pointer';
        allItem.innerHTML = `
            <input type="checkbox" checked class="form-check-input mt-0" id="cat-all">
            <span class="fw-bold">全选 / 反选</span>
        `;
        allItem.onclick = (e) => {
             e.stopPropagation();
             const cb = allItem.querySelector('input');
             if (e.target !== cb) cb.checked = !cb.checked;
             this.toggleAllCategories(cb.checked);
        };
        this.menu.prepend(allItem);

        this.container.appendChild(this.menu);
        this.container.appendChild(this.button);

        // 交互逻辑：悬停显示，移出延迟隐藏
        
        // 按钮悬停
        this.button.onmouseenter = (e) => {
             this.showCategoryMenu();
        };

        // 容器移出
        this.container.onmouseleave = (e) => {
             this.hideCategoryMenu();
        };

        return this.container;
    }

    onRemove() {
        this.container.parentNode.removeChild(this.container);
        this.map = undefined;
    }

    isMouseOverMenu() {
        if (!this.menu || this.menu.style.display === 'none') return false;
        
        const rect = this.menu.getBoundingClientRect();
        const x = this.lastMouseX;
        const y = this.lastMouseY;
        
        // 增加一点缓冲区域
        return (x >= rect.left - 10 && x <= rect.right + 10 &&
                y >= rect.top - 10 && y <= rect.bottom + 10);
    }
    
    isMouseOverButton() {
        const rect = this.button.getBoundingClientRect();
        const x = this.lastMouseX;
        const y = this.lastMouseY;
        return (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom);
    }

    showCategoryMenu() {
        this.menu.style.display = 'block';
        // 调整位置：如果按钮在右侧，向左弹出
        // 获取控件位置
        // 注意：MapLibre控件通常是 absolute 的
    }
    
    // 更新标记时间范围（从 LayerToggleControl 调用）
    updateMarkerTimeRangeUI(range) {
         // 这里可以添加逻辑来在菜单中反映时间范围，如果需要的话
         this.triggerUpdates();
    }
    
    updateTimeRangeUI(range) {
        // 与 updateMarkerTimeRangeUI 类似
    }

    hideCategoryMenu() {
         // 延迟隐藏，给用户时间移动鼠标到菜单
         setTimeout(() => {
             if (!this.container.matches(':hover')) {
                 this.menu.style.display = 'none';
             }
         }, 200);
    }

    toggleCategory(cat, checked) {
        if (checked) {
            if (!this.selectedCategories.includes(cat)) {
                this.selectedCategories.push(cat);
            }
        } else {
            this.selectedCategories = this.selectedCategories.filter(c => c !== cat);
        }
        
        // 更新“全选”状态
        const allCb = this.menu.querySelector('#cat-all');
        if (allCb) {
            allCb.checked = this.selectedCategories.length === Object.keys(FAULT_CATEGORY_COLORS).length;
        }

        this.triggerUpdates();
    }

    toggleAllCategories(checked) {
        const checkboxes = this.menu.querySelectorAll('input[type="checkbox"]:not(#cat-all)');
        checkboxes.forEach(cb => cb.checked = checked);
        
        if (checked) {
            this.selectedCategories = Object.keys(FAULT_CATEGORY_COLORS);
        } else {
            this.selectedCategories = [];
        }
        
        this.triggerUpdates();
    }
    
    // 快捷方法：供外部调用获取当前选中的分类
    getSelectedCategories() {
        return this.selectedCategories;
    }

    triggerUpdates() {
        if (window.updateMapState) {
            window.updateMapState();
        } else {
            console.warn('window.updateMapState is not defined');
        }
        // 不再更新按钮状态，因为取消了选中状态
    }

    // 外部调用，更新按钮状态 (已废弃，不再使用)
    updateButtonState() {
        // 空实现，不再更新按钮状态
    }
}
