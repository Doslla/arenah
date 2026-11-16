import api from '../api/client'

// Retire les champs vides pour que le back-end applique ses valeurs par défaut
const nettoyer = (data) =>
  Object.fromEntries(Object.entries(data).filter(([, v]) => v !== '' && v !== undefined))

// Même interface que le faux service du Sprint 1 : list / create / update / remove
export function createApiService(chemin, params = {}) {
  return {
    list: () => api.get(chemin, { params }).then((r) => r.data),
    create: (item) => api.post(chemin, nettoyer(item)).then((r) => r.data),
    update: (id, item) => api.put(`${chemin}/${id}`, nettoyer(item)).then((r) => r.data),
    remove: (id) => api.delete(`${chemin}/${id}`).then(() => true),
  }
}
