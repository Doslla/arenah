import { createMockService } from './mockService'
import { createApiService } from './apiService'
import { conges, budgets, depenses } from '../data/mock'

// Branchés sur FastAPI (Sprint 2)
export const unitesService = createApiService('/unites')
export const employesService = createApiService('/employes')
export const postesService = createApiService('/postes')

// Encore sur données fictives : branchés au J3
export const congesService = createMockService(conges)
export const budgetsService = createMockService(budgets)
export const depensesService = createMockService(depenses)
