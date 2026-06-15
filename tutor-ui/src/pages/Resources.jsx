import React, { useState, useMemo } from 'react';
import { useToast } from '../context/ToastContext';

const folders = [
  { id: 'root', name: 'All Files', parent: null },
  { id: 'materials', name: 'Course Materials', parent: 'root' },
  { id: 'notes', name: 'Student Notes', parent: 'root' },
  { id: 'shared', name: 'Shared Documents', parent: 'root' },
  { id: 'rag', name: 'RAG Deep Dive', parent: 'materials' },
  { id: 'agents', name: 'AI Agents', parent: 'materials' },
];

const files = [
  { id: 1, name: 'RAG Architecture Overview.pdf', folder: 'rag', type: 'pdf', size: '2.4 MB', uploadedBy: 'Prof. Chen', date: '2025-01-15', downloads: 42 },
  { id: 2, name: 'Vector Database Comparison.xlsx', folder: 'rag', type: 'xlsx', size: '1.1 MB', uploadedBy: 'Prof. Chen', date: '2025-01-18', downloads: 28 },
  { id: 3, name: 'Agent Frameworks Guide.md', folder: 'agents', type: 'md', size: '156 KB', uploadedBy: 'Prof. Chen', date: '2025-01-20', downloads: 35 },
  { id: 4, name: 'My LLM Study Notes.pdf', folder: 'notes', type: 'pdf', size: '890 KB', uploadedBy: 'Alex Chen', date: '2025-01-22', downloads: 3 },
  { id: 5, name: 'RAG Exercise Solutions.pdf', folder: 'shared', type: 'pdf', size: '3.2 MB', uploadedBy: 'Prof. Chen', date: '2025-01-25', downloads: 67 },
  { id: 6, name: 'Multimodal AI Cheat Sheet.pdf', folder: 'shared', type: 'pdf', size: '1.8 MB', uploadedBy: 'Maria Garcia', date: '2025-01-26', downloads: 19 },
  { id: 7, name: 'Prompt Engineering Patterns.md', folder: 'notes', type: 'md', size: '45 KB', uploadedBy: 'Sofia Park', date: '2025-01-27', downloads: 12 },
  { id: 8, name: 'Course Syllabus.pdf', folder: 'root', type: 'pdf', size: '520 KB', uploadedBy: 'Prof. Chen', date: '2025-01-10', downloads: 89 },
];

const fileIcons = {
  pdf: '📕',
  xlsx: '📊',
  md: '📝',
  txt: '📄',
  default: '📄',
};

const fileTypeLabels = {
  pdf: 'PDF',
  xlsx: 'Spreadsheet',
  md: 'Markdown',
  txt: 'Text',
  default: 'File',
};

export default function Resources() {
  const [activeFolder, setActiveFolder] = useState('root');
  const [search, setSearch] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [uploadName, setUploadName] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const { addToast } = useToast();

  const folderPath = useMemo(() => {
    const path = [];
    let current = folders.find(f => f.id === activeFolder);
    while (current) {
      path.unshift(current);
      current = folders.find(f => f.id === current.parent);
    }
    return path;
  }, [activeFolder]);

  const currentFiles = useMemo(() => {
    let data = files.filter(f => f.folder === activeFolder);
    if (search) data = data.filter(f => f.name.toLowerCase().includes(search.toLowerCase()));
    return data;
  }, [activeFolder, search]);

  const handleUpload = () => {
    if (!uploadName.trim()) return;
    addToast(`Uploaded "${uploadName}" to current folder`, 'success', 3000);
    setUploadName('');
    setShowUpload(false);
  };

  const handleDownload = (file) => {
    addToast(`Downloaded "${file.name}"`, 'success', 3000);
    setSelectedFile(null);
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-[var(--c-primary)] to-[var(--c-secondary)] bg-clip-text text-transparent">Resources</h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">Course materials, shared notes, and reference documents</p>
        </div>
        <button onClick={() => setShowUpload(!showUpload)} className="btn-primary">
          ⬆️ Upload File
        </button>
      </div>

      {/* Upload panel */}
      {showUpload && (
        <div className="card p-4 animate-fadeInUp">
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">File Name</label>
              <input type="text" placeholder="e.g. My Notes.pdf" value={uploadName} onChange={e => setUploadName(e.target.value)} className="input w-full" />
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">Folder</label>
              <select className="input w-full" value={activeFolder} onChange={e => setActiveFolder(e.target.value)}>
                {folders.filter(f => f.id !== 'root').map(f => (
                  <option key={f.id} value={f.id}>{f.name}</option>
                ))}
              </select>
            </div>
            <button onClick={handleUpload} className="btn-primary py-2.5">Upload</button>
            <button onClick={() => setShowUpload(false)} className="btn-secondary py-2.5">Cancel</button>
          </div>
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Folder tree */}
        <div className="lg:w-64 space-y-2">
          <div className="card p-3">
            <h3 className="text-xs font-bold uppercase text-[var(--text-muted)] tracking-wider mb-3">Folders</h3>
            <div className="space-y-1">
              {folders.filter(f => f.parent === 'root').map(folder => (
                <div key={folder.id}>
                  <button
                    onClick={() => setActiveFolder(folder.id)}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-[var(--r-md)] text-sm transition-all
                      ${activeFolder === folder.id ? 'bg-[var(--c-primary)]/15 text-[var(--c-primary)] font-medium' : 'text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]'}`}
                  >
                    📁 {folder.name}
                  </button>
                  <div className="ml-4 space-y-1 mt-1">
                    {folders.filter(f => f.parent === folder.id).map(sub => (
                      <button
                        key={sub.id}
                        onClick={() => setActiveFolder(sub.id)}
                        className={`w-full flex items-center gap-2 px-3 py-2 rounded-[var(--r-md)] text-sm transition-all
                          ${activeFolder === sub.id ? 'bg-[var(--c-primary)]/15 text-[var(--c-primary)] font-medium' : 'text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]'}`}
                      >
                        📂 {sub.name}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card p-3">
            <h3 className="text-xs font-bold uppercase text-[var(--text-muted)] tracking-wider mb-3">Storage</h3>
            <div className="text-sm text-[var(--text-secondary)]">
              <div className="flex justify-between mb-1">
                <span>Used</span>
                <span className="font-medium text-[var(--text-primary)]">12.4 MB</span>
              </div>
              <div className="w-full h-2 bg-[var(--bg-surface)] rounded-full overflow-hidden">
                <div className="h-full bg-[var(--c-primary)] rounded-full" style={{ width: '24%' }}></div>
              </div>
              <div className="flex justify-between mt-1 text-xs text-[var(--text-muted)]">
                <span>of 50 MB</span>
                <span>24%</span>
              </div>
            </div>
          </div>
        </div>

        {/* File list */}
        <div className="flex-1 space-y-4">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
            {folderPath.map((f, i) => (
              <React.Fragment key={f.id}>
                {i > 0 && <span>/</span>}
                <button onClick={() => setActiveFolder(f.id)} className={`hover:text-[var(--c-primary)] transition-colors ${i === folderPath.length - 1 ? 'font-medium text-[var(--text-primary)]' : ''}`}>
                  {f.name}
                </button>
              </React.Fragment>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <input type="text" placeholder="Search files..." value={search} onChange={e => setSearch(e.target.value)} className="input flex-1" />
          </div>

          <div className="card overflow-hidden">
            {currentFiles.length > 0 ? (
              <div className="divide-y divide-[var(--border)]">
                {currentFiles.map(file => (
                  <div key={file.id} className="flex items-center gap-4 px-5 py-4 hover:bg-[var(--bg-surface)]/50 transition-colors group">
                    <div className="text-2xl">{fileIcons[file.type] || fileIcons.default}</div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-[var(--text-primary)] truncate">{file.name}</div>
                      <div className="text-xs text-[var(--text-muted)] mt-0.5">
                        {fileTypeLabels[file.type] || fileTypeLabels.default} · {file.size} · Uploaded by {file.uploadedBy} · {file.date}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-[var(--text-muted)]">{file.downloads} downloads</span>
                      <button onClick={() => setSelectedFile(file)} className="btn-secondary text-xs py-1.5 px-3 opacity-0 group-hover:opacity-100 transition-opacity">Actions</button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-12 text-center">
                <div className="text-4xl mb-3">📂</div>
                <p className="text-sm text-[var(--text-muted)]">No files in this folder.</p>
                <button onClick={() => setShowUpload(true)} className="text-sm text-[var(--c-primary)] hover:underline mt-2">Upload your first file</button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* File actions modal */}
      {selectedFile && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setSelectedFile(null)}>
          <div className="card max-w-md w-full p-6 space-y-4 animate-scaleIn" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3">
              <div className="text-3xl">{fileIcons[selectedFile.type] || fileIcons.default}</div>
              <div>
                <h3 className="font-bold text-[var(--text-primary)]">{selectedFile.name}</h3>
                <p className="text-xs text-[var(--text-muted)]">{selectedFile.size} · {selectedFile.date}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button onClick={() => handleDownload(selectedFile)} className="btn-primary py-2.5">⬇️ Download</button>
              <button onClick={() => { addToast(`Shared "${selectedFile.name}"`, 'success'); setSelectedFile(null); }} className="btn-secondary py-2.5">🔗 Share</button>
              <button onClick={() => { addToast(`Moved "${selectedFile.name}" to notes`, 'success'); setSelectedFile(null); }} className="btn-secondary py-2.5">📁 Move</button>
              <button onClick={() => { addToast(`Deleted "${selectedFile.name}"`, 'success'); setSelectedFile(null); }} className="btn-secondary py-2.5 text-red-400 hover:text-red-300">🗑️ Delete</button>
            </div>
            <button onClick={() => setSelectedFile(null)} className="btn-secondary w-full py-2.5">Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
