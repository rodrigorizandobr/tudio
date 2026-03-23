import * as icons from 'lucide-vue-next';

const keys = Object.keys(icons);
console.log(`Total keys: ${keys.length}`);

const duplicateCheck = new Set();
const duplicates = [];

keys.forEach(key => {
    if (duplicateCheck.has(key)) {
        duplicates.push(key);
    }
    duplicateCheck.add(key);
});

console.log(`Duplicates in keys: ${duplicates.length}`);

// Print first 20 keys to see if there are obvious pairs like Check, CheckCircle etc which are distinct.
// But maybe aliases?
console.log('First 20 keys:', keys.slice(0, 20));

// Check if maybe we have 'Activity' and 'activity'?
const lowerKeys = keys.map(k => k.toLowerCase());
const lowerSet = new Set(lowerKeys);
if (lowerSet.size !== keys.length) {
    console.log("Found case-insensitive duplicates (unlikely to be the issue but good to know)");
}

// Check filtering used in the app
const filtered = Object.entries(icons)
    .filter(([name]) => name !== 'createLucideIcon' && name !== 'default')
    .map(([name]) => name);

console.log(`Filtered count: ${filtered.length}`);

// Check for aliases pointing to same component
const componentMap = new Map();
const aliases = [];

Object.entries(icons).forEach(([key, value]) => {
    if (key === 'createLucideIcon' || key === 'default') return;
    if (componentMap.has(value)) {
        aliases.push({ original: componentMap.get(value), alias: key });
    } else {
        componentMap.set(value, key);
    }
});

console.log(`Found ${aliases.length} aliases (different names for same component object)`);
if (aliases.length > 0) {
    console.log('Sample aliases:', aliases.slice(0, 10));
}
