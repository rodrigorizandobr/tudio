import * as icons from 'lucide-vue-next'


// Cache the icons array to avoid re-computation
const getUniqueIcons = () => {
    const componentMap = new Map<any, string>()

    // First pass: Find the shortest name for each component
    for (const [name, component] of Object.entries(icons)) {
        if (name === 'createLucideIcon' || name === 'default') continue

        const existingName = componentMap.get(component)
        if (!existingName || name.length < existingName.length) {
            componentMap.set(component, name)
        }
    }

    // Second pass: Build the array using the canonical names
    return Array.from(componentMap.entries())
        .map(([component, name]) => ({
            name,
            component,
            label: name
        }))
        .sort((a, b) => a.name.localeCompare(b.name))
}

const ALL_ICONS = getUniqueIcons()

export const getAllIcons = () => ALL_ICONS

export const getIconComponent = (name: string) => {
    // @ts-expect-error - dynamic import
    return icons[name] || icons.Bot
}
