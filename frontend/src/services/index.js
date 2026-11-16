import { createApiService } from './apiService'

// Services branchés sur FastAPI (les pages J3 appellent l'API directement)
export const unitesService = createApiService('/unites')
export const employesService = createApiService('/employes')
export const postesService = createApiService('/postes')
