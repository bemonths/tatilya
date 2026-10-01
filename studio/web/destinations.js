import {esc} from './api.js';

export function destinationOptions(destinations, selected) {
  return destinations.map(d=>`<option value="${esc(d.id)}" ${d.id===selected?'selected':''}>${esc(d.name)} · ${esc(d.subtitle || '')}</option>`).join('');
}

export function storedDestination(storage) {
  try { return storage.getItem('studio.destination_id') || null; } catch { return null; }
}

export function persistDestination(storage, id) {
  try { storage.setItem('studio.destination_id',id); } catch { /* Storage can be disabled. */ }
}

export function resetDestinationState(state, screens) {
  for (const screen of screens) {
    screen.invalidate();
    const sequence=screen.sequence;
    Object.assign(screen,new screen.constructor());
    screen.snapshot=null;
    screen.data=null;
    screen.selectedRecord=null;
    screen.sequence=sequence;
  }
  Object.assign(state,{data:null,selected:null,search:'',category:'',region:'',archived:false,editing:null});
}

export function destinationRows(rows, destination) {
  return destination ? rows.filter(row=>row.destination_id===destination.id) : rows;
}
