import * as icons from 'lucide-vue-next';

// Replicate the logic
const componentMap = new Map();

for (const [name, component] of Object.entries(icons)) {
    if (name === 'createLucideIcon' || name === 'default') continue;

    const existingName = componentMap.get(component);
    if (!existingName || name.length < existingName.length) {
        componentMap.set(component, name);
    }
}

const uniqueIcons = Array.from(componentMap.entries()).map(([component, name]) => name);

console.log(`Original count: ${Object.keys(icons).length}`);
console.log(`Unique count: ${uniqueIcons.length}`);
console.log('Sample unique names:', uniqueIcons.slice(0, 10));

// Check if we still have collisions like Activity vs ActivityIcon
const Activity = uniqueIcons.includes('Activity');
const ActivityIcon = uniqueIcons.includes('ActivityIcon');

console.log(`Has 'Activity': ${Activity}`);
console.log(`Has 'ActivityIcon': ${ActivityIcon}`);

if (Activity && !ActivityIcon) {
    console.log("SUCCESS: Deduplication preferred shorter name.");
} else if (!Activity && ActivityIcon) {
    console.log("WARNING: Deduplication preferred longer name?");
} else {
    console.log("FAILURE: Both or neither present.");
}
