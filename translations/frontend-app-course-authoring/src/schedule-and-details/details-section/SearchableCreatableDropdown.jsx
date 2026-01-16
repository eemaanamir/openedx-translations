import React, { useState } from 'react';
import { Form, Dropdown } from '@openedx/paragon';

import { getConfig } from '@edx/frontend-platform';
import { getAuthenticatedHttpClient } from '@edx/frontend-platform/auth';

const SearchableCreatableDropdown = ({ 
    options, 
    value, 
    onChange, 
    placeholder,
    onCreateTopic 
  }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [isCreating, setIsCreating] = useState(false);
  
    const filteredOptions = options.filter(option =>
      option.toLowerCase().includes(searchTerm.toLowerCase())
    );
  
    const showCreateOption = searchTerm.trim() && 
      !options.some(opt => opt.toLowerCase() === searchTerm.trim().toLowerCase());
  
    const handleCreateTopic = async () => {
      if (!searchTerm.trim()) return;
      
      setIsCreating(true);
      try {
        const { data } = await getAuthenticatedHttpClient().post(
          `${getConfig().STUDIO_BASE_URL}/wikimedia_general/api/v0/topics`,
          { name: searchTerm.trim() }
        );
        
        // First update the selection
        onChange(data.name);
        // Then notify parent about the new topic
        await onCreateTopic(data.name);
        // Clear search and close dropdown
        setSearchTerm('');
        setIsOpen(false);
  
      } catch (error) {
        console.error('Error creating topic:', error);
        alert('Network error: Could not create topic');
      } finally {
        setIsCreating(false);
      }
    };
  
    return (
      <div className="searchable-creatable-dropdown">
        <Dropdown show={isOpen} onToggle={setIsOpen} className="bg-white">
          <Dropdown.Toggle variant="outline-primary" id="topicDropdown">
            {value || placeholder}
          </Dropdown.Toggle>
          <Dropdown.Menu>
            <div className="px-3 py-2">
              <Form.Control
                type="text"
                placeholder="Search or create topic..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onClick={(e) => e.stopPropagation()}
              />
            </div>
            <Dropdown.Divider />
            <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
              {filteredOptions.length > 0 ? (
                filteredOptions.map((option) => (
                  <Dropdown.Item
                    key={option}
                    onClick={() => {
                      onChange(option);
                      setSearchTerm('');
                      setIsOpen(false);
                    }}
                  >
                    {option}
                  </Dropdown.Item>
                ))
              ) : (
                !showCreateOption && (
                  <Dropdown.Item disabled>No topics found</Dropdown.Item>
                )
              )}
              {showCreateOption && (
                <>
                  <Dropdown.Divider />
                  <Dropdown.Item
                    onClick={handleCreateTopic}
                    disabled={isCreating}
                    className="text-primary font-weight-bold"
                  >
                    {isCreating ? 'Creating...' : `+ Create "${searchTerm}"`}
                  </Dropdown.Item>
                </>
              )}
            </div>
          </Dropdown.Menu>
        </Dropdown>
      </div>
    );
  };
  // ========== END: CUSTOM TOPIC DROPDOWN ENHANCEMENT ==========
  
  export default SearchableCreatableDropdown;