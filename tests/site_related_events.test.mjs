import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const template = fs.readFileSync(new URL('../netbox_otnfaults/templates/netbox_otnfaults/inc/site_related_events.html', import.meta.url), 'utf8');
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1];

function render({type = 'cutovers', count = 4, loading = false, header = '相关对象'} = {}) {
    const base = `/netbox/plugins/otnfaults/${type}/`;
    const links = [];
    function link(href, wrapped = false) {
        const item = {
            href,
            getAttribute: () => href,
            closest: () => wrapped ? {remove: () => item.remove()} : null,
            remove: () => links.splice(links.indexOf(item), 1),
        };
        return item;
    }
    links.push(link(`${base}?${type === 'paths' ? 'site_a_id' : 'interruption_location_a_id'}=169`));
    links.push(link(`${base}?${type === 'paths' ? 'site_z_id' : 'interruption_location_id'}=169`, true));
    const other = link(`/netbox/plugins/otnfaults/${type === 'paths' ? 'faults' : 'paths'}/?site_a_id=169`);
    links.push(other);
    const unified = count ? link(`${base}?site=169`) : null;
    const source = {
        dataset: {relatedListUrl: base},
        querySelector: () => unified,
        remove: () => { source.removed = true; },
    };
    const list = {
        querySelectorAll: () => [...links],
        appendChild: item => links.push(item),
    };
    let onReady;
    const document = {
        currentScript: {previousElementSibling: source},
        readyState: loading ? 'loading' : 'complete',
        querySelectorAll: () => [{querySelector: selector => selector === '.card-header' ? {innerText: header} : list}],
        addEventListener: (event, callback) => { onReady = callback; },
    };
    vm.runInNewContext(script, {document, URL, window: {location: {href: 'https://netbox.example/netbox/dcim/sites/169/'}}});
    if (loading) {
        assert.equal(links.length, 3);
        onReady();
    }
    assert.deepEqual(links, unified ? [other, unified] : [other]);
    assert.equal(source.removed, true);
}

test('cutovers combine A and Z links into a single site link', () => render());
test('faults use the same link replacement after DOM load', () => render({type: 'faults', loading: true}));
test('zero visible events removes native relation links', () => render({count: 0}));
test('English related objects heading is supported', () => render({header: 'Related Objects'}));
test('paths combine A/Z links and preserve other object links', () => render({type: 'paths'}));
test('zero visible paths removes both native links', () => render({type: 'paths', count: 0}));

test('all related object templates use the shared site link', () => {
    for (const [file, route] of [['site_otn_faults.html', 'otnfault_list'], ['site_cutover_tasks.html', 'cutovertask_list'], ['site_otn_paths.html', 'otnpath_list']]) {
        const source = fs.readFileSync(new URL(`../netbox_otnfaults/templates/netbox_otnfaults/inc/${file}`, import.meta.url), 'utf8');
        assert.ok(source.includes(route));
        assert.ok(source.includes('site_related_events.html'));
    }
    assert.ok(template.includes('?site={{ site_id }}'));
});
