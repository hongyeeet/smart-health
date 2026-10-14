import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { request } from '@/data/repositories/http'

/**
 * Is the typed or scanned name outside what Equinox is for? GET /medications/scope answers with a gentle flag only: it never
 * blocks a save. The name is checked a moment after the person stops typing, so the page does not ask on every letter.
 * Returns false while unknown (the note simply does not show).
 */
export function useMedicineScope(name: string, kind: string): boolean {
  const [settled, setSettled] = useState(name)
  useEffect(() => {
    const id = setTimeout(() => setSettled(name), 500)
    return () => clearTimeout(id)
  }, [name])
  const term = settled.trim()
  const { data } = useQuery({
    queryKey: ['medicineScope', term, kind],
    queryFn: () => request<{ outOfScope: boolean }>(`/medications/scope?name=${encodeURIComponent(term)}&kind=${encodeURIComponent(kind)}`),
    enabled: term.length >= 3,
    staleTime: 10 * 60_000,
  })
  return data?.outOfScope ?? false
}
