export const DEVISE = 'MGA' // affiché « MGA » ; le paramètre « devise » de la plateforme vaut « Ar »

export const formatMontant = (v) =>
  new Intl.NumberFormat('fr-FR', { style: 'currency', currency: DEVISE, maximumFractionDigits: 0 }).format(v ?? 0)

export const formatDate = (d) => (d ? new Date(d).toLocaleDateString('fr-FR') : '—')
