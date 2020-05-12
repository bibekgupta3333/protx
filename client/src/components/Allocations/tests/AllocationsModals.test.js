import React from 'react';
import { render } from '@testing-library/react';
import { BrowserRouter as Wrapper } from 'react-router-dom';
import { NewAllocReq } from '../AllocationsModals';

describe('Allocations Request Form', () => {
  const isOpen = true;
  it('should tell the user what form they are viewing', () => {
    const { getByText } = render(
      <Wrapper>
        <NewAllocReq isOpen toggle={() => !isOpen} />
      </Wrapper>
    );
    expect(getByText('Manage Allocations')).toBeDefined();
  });
  it('have a body with content for the user', () => {
    const { getByTestId } = render(
      <Wrapper>
        <NewAllocReq isOpen toggle={() => !isOpen} />
      </Wrapper>
    );
    expect(getByTestId('request-body')).toBeDefined();
  });
});

describe('View Team Modal', () => {
  it.todo(
    'assert that the components of view team modal are showing relevant information for the user'
  );
});