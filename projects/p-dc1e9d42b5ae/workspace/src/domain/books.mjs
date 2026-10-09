export function searchBooks(books,q=''){q=q.trim().toLowerCase();return books.filter(b=>`${b.title}\n${b.author}`.toLowerCase().includes(q));}
export function counts(books){return {total:books.length,available:books.filter(b=>b.status==='available').length,borrowed:books.filter(b=>b.status==='borrowed').length};}
