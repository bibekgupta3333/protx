import React from 'react';
import { useSelector, useDispatch } from 'react-redux';
import PropTypes from 'prop-types';
import { Button } from 'reactstrap';
import './DataFilesToolbar.scss';

export const ToolbarButton = ({ text, icon, onClick, disabled }) => {
  return (
    <Button
      disabled={disabled}
      onClick={onClick}
      className="data-files-toolbar-button"
    >
      <i
        className={`${icon.prefix} ${icon.prefix}-${icon.iconName}`}
        data-testid="toolbar-icon"
      />
      <span className="toolbar-button-text">{text}</span>
    </Button>
  );
};
ToolbarButton.defaultProps = {
  onClick: () => {},
  disabled: true
};
ToolbarButton.propTypes = {
  onClick: PropTypes.func,
  disabled: PropTypes.bool,
  text: PropTypes.string.isRequired,
  icon: PropTypes.shape({
    prefix: PropTypes.string,
    iconName: PropTypes.string
  }).isRequired
};

const DataFilesToolbar = ({ scheme }) => {
  const dispatch = useDispatch();

  const selectedFiles = useSelector(state =>
    state.files.selected.FilesListing.map(
      i => state.files.listing.FilesListing[i]
    )
  );

  const toggleRenameModal = () =>
    dispatch({
      type: 'DATA_FILES_TOGGLE_MODAL',
      payload: {
        operation: 'rename',
        props: { selectedFile: selectedFiles[0] }
      }
    });

  const toggleMoveModal = () =>
    dispatch({
      type: 'DATA_FILES_TOGGLE_MODAL',
      payload: { operation: 'move', props: { selectedFiles } }
    });

  const toggleCopyModal = () =>
    dispatch({
      type: 'DATA_FILES_TOGGLE_MODAL',
      payload: { operation: 'copy', props: { selectedFiles } }
    });

  const download = () => {
    dispatch({
      type: 'DATA_FILES_DOWNLOAD',
      payload: { file: selectedFiles[0] }
    });
  };

  const trash = () => {
    dispatch({
      type: 'DATA_FILES_TOGGLE_MODAL',
      payload: { operation: 'trash', props: { selectedFiles } }
    });
  };

  const canRename = selectedFiles.length === 1 && scheme === 'private';
  const canMove = selectedFiles.length > 0 && scheme === 'private';
  const canCopy = selectedFiles.length > 0 && scheme === 'private';
  const canDownload =
    selectedFiles.length === 1 && selectedFiles[0].format !== 'folder';
  const canTrash = selectedFiles.length > 0 && scheme === 'private';

  return (
    <>
      <div id="data-files-toolbar-button-row">
        <ToolbarButton
          text="Rename"
          onClick={toggleRenameModal}
          icon={{ prefix: 'icon-action', iconName: 'rename' }}
          disabled={!canRename}
        />
        <ToolbarButton
          text="Move"
          onClick={toggleMoveModal}
          icon={{ prefix: 'icon-action', iconName: 'move' }}
          disabled={!canMove}
        />
        <ToolbarButton
          text="Copy"
          onClick={toggleCopyModal}
          icon={{ prefix: 'icon-action', iconName: 'copy' }}
          disabled={!canCopy}
        />
        <ToolbarButton
          text="Download"
          icon={{ prefix: 'icon-action', iconName: 'download' }}
          onClick={download}
          disabled={!canDownload}
        />
        <ToolbarButton
          text="Trash"
          icon={{ prefix: 'icon-action', iconName: 'rename' }}
          onClick={trash}
          disabled={!canTrash}
        />
      </div>
    </>
  );
};
DataFilesToolbar.propTypes = {
  scheme: PropTypes.string.isRequired
};

export default DataFilesToolbar;