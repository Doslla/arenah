export function createMockService(initial) {
  let data = [...initial]; let nextId = Math.max(0, ...data.map((d) => d.id)) + 1
  const delay = (v) => new Promise((r) => setTimeout(() => r(v), 150))
  return { list: () => delay([...data]), create: (item) => { const n = { ...item, id: nextId++ }; data.push(n); return delay(n) },
    update: (id, item) => { data = data.map((d) => (d.id === id ? { ...item, id } : d)); return delay({ ...item, id }) },
    remove: (id) => { data = data.filter((d) => d.id !== id); return delay(true) } }
}
