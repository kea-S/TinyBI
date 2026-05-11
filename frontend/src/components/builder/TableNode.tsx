import { memo } from 'react';
import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { Table as TableIcon } from 'lucide-react';

export type TableNodeData = {
  name: string;
  columns: {
    id: string;
    columnName: string;
  }[];
  isSelected?: boolean;
};

export const TableNode = memo(({ data }: NodeProps<Node<TableNodeData>>) => {
  return (
    <div className={`min-w-[200px] rounded-xl border bg-card shadow-lg transition-all ${data.isSelected ? 'border-primary ring-2 ring-primary/20' : 'border-border'}`}>
      <div className="flex items-center gap-2 border-b border-border bg-muted/50 px-4 py-2 rounded-t-xl">
        <TableIcon className="size-4 text-primary" />
        <span className="text-sm font-semibold tracking-tight">{data.name || 'Untitled Table'}</span>
      </div>
      
      <div className="flex flex-col py-1">
        {data.columns.map((col) => (
          <div key={col.id} className="relative flex items-center justify-between px-4 py-2 hover:bg-muted/30 transition-colors group">
            <Handle
              type="target"
              position={Position.Left}
              id={`${col.id}-target`}
              className="!size-4 !bg-primary border-2 border-white dark:border-slate-900 hover:!scale-125 transition-transform"
            />
            
            <span className="text-xs font-medium text-foreground">{col.columnName || 'Untitled Column'}</span>

            <Handle
              type="source"
              position={Position.Right}
              id={`${col.id}-source`}
              className="!size-4 !bg-primary !rounded-none border-none hover:!scale-125 transition-transform"
              style={{ clipPath: 'polygon(0 0, 100% 50%, 0 100%)' }}
            />
          </div>
        ))}
      </div>
      
      {data.columns.length === 0 && (
        <div className="px-4 py-4 text-center text-[10px] text-muted-foreground uppercase tracking-widest">
          No Columns
        </div>
      )}
    </div>
  );
});

TableNode.displayName = 'TableNode';
