'use client'

import { useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  AlertCircle,
  Bell,
  CheckCircle,
  FileSpreadsheet,
  HelpCircle,
  Loader2,
  LogOut,
  RefreshCw,
  Search,
  Upload,
  X,
} from 'lucide-react'
import { getUserDisplayName, useAuth } from '@/components/AuthProvider'
import { uploadDataset, type DatasetColumnSchemaInput } from '@/lib/api'

type UploadColumn = DatasetColumnSchemaInput

function parseCsvLine(line: string) {
  const values: string[] = []
  let current = ''
  let inQuotes = false

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index]
    const next = line[index + 1]

    if (char === '"' && inQuotes && next === '"') {
      current += '"'
      index += 1
    } else if (char === '"') {
      inQuotes = !inQuotes
    } else if (char === ',' && !inQuotes) {
      values.push(current.trim())
      current = ''
    } else {
      current += char
    }
  }

  values.push(current.trim())
  return values.map((value) => value.replace(/^"|"$/g, '').trim()).filter(Boolean)
}

function extractCsvHeaders(csvText: string) {
  const headerLine = csvText.split(/\r?\n/).find((line) => line.trim().length > 0)
  return headerLine ? parseCsvLine(headerLine) : []
}

export function Navbar() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { error, isAuthenticated, loading, logout, refresh, user } = useAuth()
  const [uploadOpen, setUploadOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [columns, setColumns] = useState<UploadColumn[]>([])
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  const userName = getUserDisplayName(user)
  const initials =
    isAuthenticated && userName !== 'Signed in'
      ? userName
          .split(/\s+/)
          .map((part) => part[0])
          .join('')
          .slice(0, 2)
          .toUpperCase()
      : 'AI'

  const canSubmit = useMemo(
    () => Boolean(selectedFile && columns.length > 0 && columns.every((column) => column.description.trim()) && !uploading),
    [columns, selectedFile, uploading],
  )

  const resetUpload = () => {
    setSelectedFile(null)
    setColumns([])
    setUploadError(null)
    setUploadSuccess(null)
    setUploading(false)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const openFilePicker = () => {
    setUploadError(null)
    setUploadSuccess(null)
    fileInputRef.current?.click()
  }

  const handleFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setUploadError(null)
    setUploadSuccess(null)

    if (!file.name.toLowerCase().endsWith('.csv')) {
      setUploadOpen(true)
      setUploadError('Please select a CSV file.')
      setSelectedFile(null)
      setColumns([])
      return
    }

    try {
      const text = await file.slice(0, 64 * 1024).text()
      const headers = extractCsvHeaders(text)
      if (headers.length === 0) {
        throw new Error('No column headers found in this CSV.')
      }

      setSelectedFile(file)
      setColumns(headers.map((field) => ({ field, description: '' })))
      setUploadOpen(true)
    } catch (err) {
      setSelectedFile(null)
      setColumns([])
      setUploadOpen(true)
      setUploadError(err instanceof Error ? err.message : 'Could not read CSV headers.')
    }
  }

  const updateColumnDescription = (field: string, description: string) => {
    setColumns((current) =>
      current.map((column) => (column.field === field ? { ...column, description } : column)),
    )
  }

  const closeUpload = () => {
    if (uploading) return
    setUploadOpen(false)
    resetUpload()
  }

  const handleUploadSubmit = async () => {
    if (!selectedFile || !canSubmit) return

    setUploading(true)
    setUploadError(null)
    setUploadSuccess(null)

    try {
      await uploadDataset(
        selectedFile,
        columns.map((column) => ({
          field: column.field,
          description: column.description.trim(),
        })),
      )
      setUploadSuccess('Dataset uploaded and schema saved.')
      window.dispatchEvent(new Event('dataset-uploaded'))
      window.setTimeout(() => {
        setUploadOpen(false)
        resetUpload()
        router.push('/datasets')
      }, 700)
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Dataset upload failed.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <header className="h-16 bg-sidebar/40 backdrop-blur-xl border-b border-sidebar-border flex items-center justify-between px-6 md:px-8 shrink-0">
      <div className="flex-1 max-w-md relative">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
        />
        <input
          type="text"
          placeholder="Search datasets, models, reports..."
          className="w-full pl-9 pr-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all"
        />
      </div>

      <div className="flex items-center space-x-2 md:space-x-3 ml-4">
        <button
          aria-label="Help"
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
        >
          <HelpCircle size={18} />
        </button>
        <button
          aria-label="Notifications"
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors relative"
        >
          <Bell size={18} />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-accent" />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={handleFileSelected}
        />
        <button
          onClick={openFilePicker}
          className="inline-flex items-center space-x-2 px-3 py-2 rounded-lg bg-primary/15 border border-primary/30 text-primary hover:bg-primary/25 transition-colors text-sm font-semibold"
        >
          <Upload size={14} />
          <span className="hidden sm:inline">Upload</span>
        </button>
        <button
          onClick={() => void refresh()}
          disabled={loading}
          className={`hidden lg:inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-semibold transition-colors ${
            error
              ? 'bg-destructive/10 border-destructive/30 text-destructive'
              : isAuthenticated
                ? 'bg-primary/10 border-primary/30 text-primary'
                : 'bg-white/5 border-white/10 text-muted-foreground hover:text-foreground'
          }`}
          title="Refresh backend session"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
        {isAuthenticated && (
          <button
            onClick={() => void logout()}
            className="p-2 rounded-lg text-muted-foreground hover:text-destructive hover:bg-white/5 transition-colors"
            aria-label="Log out"
            title="Log out"
          >
            <LogOut size={18} />
          </button>
        )}
        <div
          className="w-9 h-9 rounded-full bg-gradient-to-br from-secondary to-primary flex items-center justify-center text-sidebar-primary-foreground font-bold text-sm"
          title={userName}
        >
          {initials}
        </div>
      </div>

      {uploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-4xl overflow-hidden rounded-xl border border-white/10 bg-sidebar shadow-2xl mt-auto">
            <div className="flex items-start justify-between border-b border-white/10 px-5 py-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                  <FileSpreadsheet size={17} className="text-primary" />
                  Upload Dataset
                </div>
                <p className="mt-1 truncate text-xs text-muted-foreground">
                  {selectedFile ? selectedFile.name : 'Select a CSV file and define its schema.'}
                </p>
              </div>
              <button
                onClick={closeUpload}
                className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground"
                aria-label="Close upload form"
              >
                <X size={18} />
              </button>
            </div>

            <div className="max-h-[70vh] overflow-auto px-5 py-4">
              {uploadError && (
                <div className="mb-4 flex items-start gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                  <AlertCircle size={15} className="mt-0.5 shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}

              {uploadSuccess && (
                <div className="mb-4 flex items-start gap-2 rounded-lg border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-sm text-emerald-300">
                  <CheckCircle size={15} className="mt-0.5 shrink-0" />
                  <span>{uploadSuccess}</span>
                </div>
              )}

              {columns.length > 0 ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-[minmax(180px,260px)_minmax(0,1fr)] gap-3 px-1 text-[11px] uppercase tracking-widest text-muted-foreground">
                    <span>Column</span>
                    <span>Description</span>
                  </div>
                  {columns.map((column) => (
                    <div
                      key={column.field}
                      className="grid gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-3 md:grid-cols-[minmax(180px,260px)_minmax(0,1fr)]"
                    >
                      <div className="min-w-0 rounded-md border border-white/10 bg-black/20 px-3 py-2 font-mono text-xs text-primary">
                        <span className="block truncate">{column.field}</span>
                      </div>
                      <input
                        value={column.description}
                        onChange={(event) => updateColumnDescription(column.field, event.target.value)}
                        placeholder={`What does ${column.field} mean?`}
                        className="min-h-9 rounded-md border border-white/10 bg-white/5 px-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border border-white/10 bg-white/[0.03] px-4 py-8 text-center text-sm text-muted-foreground">
                  Choose a CSV file to detect columns.
                </div>
              )}
            </div>

            <div className="flex flex-col gap-3 border-t border-white/10 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
              <button
                onClick={openFilePicker}
                disabled={uploading}
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 text-sm font-semibold text-foreground transition-colors hover:border-primary/30 hover:bg-primary/10 disabled:opacity-50"
              >
                <Upload size={15} />
                Choose CSV
              </button>
              <button
                onClick={handleUploadSubmit}
                disabled={!canSubmit}
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-primary/30 bg-primary/20 px-5 text-sm font-semibold text-primary transition-colors hover:bg-primary/30 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {uploading ? <Loader2 size={16} className="animate-spin" /> : <FileSpreadsheet size={16} />}
                Save Dataset
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  )
}
