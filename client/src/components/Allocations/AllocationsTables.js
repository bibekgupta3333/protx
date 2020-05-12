import React, { useMemo } from 'react';
import { useTable, useSortBy } from 'react-table';
import { useSelector } from 'react-redux';
import { string } from 'prop-types';
import { Team, Systems, Awarded, Remaining, Expires } from './AllocationsCells';
import systemAccessor from './AllocationsUtils';

/** Custom hook to get columns and data for table */
export const useAllocations = page => {
  const allocations = useSelector(state => {
    if (page === 'expired') return state.allocations.inactive;
    return state.allocations.active;
  });
  const columns = useMemo(
    () => [
      {
        Header: 'Title',
        accessor: 'projectName',
        sortType: 'alphanumeric'
      },
      {
        Header: 'Principal Investigator',
        accessor: 'pi'
      },
      {
        Header: 'Team',
        accessor: 'projectId',
        Cell: Team
      },
      {
        Header: 'Systems',
        accessor: ({ systems }) => systemAccessor(systems, 'Systems'),
        id: 'name',
        Cell: Systems
      },
      {
        Header: 'Awarded',
        accessor: ({ systems }) => systemAccessor(systems, 'Awarded'),
        id: 'awarded',
        Cell: Awarded
      },
      {
        Header: 'Remaining',
        accessor: ({ systems }) => systemAccessor(systems, 'Remaining'),
        id: 'remaining',
        Cell: Remaining
      },
      {
        Header: 'Expires',
        accessor: ({ systems }) => systemAccessor(systems, 'Expires'),
        id: 'expires',
        Cell: Expires
      }
    ],
    [allocations]
  );
  const data = useMemo(() => allocations, [allocations]);
  return [
    {
      columns,
      data,
      initialState: { sortBy: [{ id: 'projectName' }] }
    },
    useSortBy
  ];
};

export const AllocationsTable = ({ page }) => {
  const tableAttributes = useAllocations(page);
  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    rows,
    prepareRow
  } = useTable(...tableAttributes);
  return (
    <div className="allocations-table">
      <table {...getTableProps()}>
        <thead>
          {headerGroups.map(headerGroup => (
            <tr {...headerGroup.getHeaderGroupProps()}>
              {headerGroup.headers.map(column => (
                <th {...column.getHeaderProps(column.getSortByToggleProps())}>
                  {column.render('Header')}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody {...getTableBodyProps()}>
          {rows.length ? (
            rows.map(row => {
              prepareRow(row);
              return (
                <tr {...row.getRowProps()}>
                  {row.cells.map(cell => (
                    <td {...cell.getCellProps()}>{cell.render('Cell')}</td>
                  ))}
                </tr>
              );
            })
          ) : (
            <tr>
              <td colSpan={headerGroups[0].headers.length}>
                <center>
                  You have no {`${page[0].toLocaleUpperCase()}${page.slice(1)}`}
                  {'  '}
                  allocations.
                </center>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};
AllocationsTable.propTypes = {
  page: string.isRequired
};