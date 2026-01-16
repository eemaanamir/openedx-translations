import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { useIntl } from '@edx/frontend-platform/i18n';
import { Form, Dropdown } from '@openedx/paragon';

import SectionSubHeader from '../../generic/section-sub-header';
import messages from './messages';
import SearchableCreatableDropdown from './SearchableCreatableDropdown';


const DetailsSection = ({
  language, languageOptions, topic, topicOptions, onChange,
}) => {
  const intl = useIntl();
  
  const formattedLanguage = () => {
    const result = languageOptions.find((arr) => arr[0] === language);
    return result ? result[1] : intl.formatMessage(messages.dropdownEmpty);
  };
  
  
  // ========== CUSTOM ==========
  const [localTopicOptions, setLocalTopicOptions] = useState(topicOptions);
  
  // Update local options when props change
  useEffect(() => {
    setLocalTopicOptions(topicOptions);
  }, [topicOptions]);

  const formattedTopic = () => {
    const result = localTopicOptions.find((t) => t === topic);
    return result || topic || intl.formatMessage(messages.topicDropdownEmpty);
  };
  
  const handleTopicCreation = async (newTopic) => {
    // Add new topic to local options immediately
    setLocalTopicOptions(prev => {
      if (!prev.includes(newTopic)) {
        return [...prev, newTopic];
      }
      return prev;
    });
    // Optionally trigger parent component refresh
    console.log('New topic created:', newTopic);
  };
  // ========== END ==========

  return (
    <section className="section-container details-section">
      <SectionSubHeader
        title={intl.formatMessage(messages.detailsTitle)}
        description={intl.formatMessage(messages.detailsDescription)}
      />
      <Form.Group className="form-group-custom dropdown-language">
        <Form.Label>{intl.formatMessage(messages.dropdownLabel)}</Form.Label>
        <Dropdown className="bg-white">
          <Dropdown.Toggle variant="outline-primary" id="languageDropdown">
            {formattedLanguage()}
          </Dropdown.Toggle>
          <Dropdown.Menu>
            {languageOptions.map((option) => (
              <Dropdown.Item
                key={option[0]}
                onClick={() => onChange(option[0], 'language')}
              >
                {option[1]}
              </Dropdown.Item>
            ))}
          </Dropdown.Menu>
        </Dropdown>
        <Form.Control.Feedback>
          {intl.formatMessage(messages.dropdownHelpText)}
        </Form.Control.Feedback>
      </Form.Group>

      {/* ========== START: MODIFIED TOPIC DROPDOWN ========== */}
      <Form.Group className="form-group-custom dropdown-topic">
        <Form.Label>{intl.formatMessage(messages.topicDropdownLabel)}</Form.Label>
        <SearchableCreatableDropdown
          options={localTopicOptions}
          value={formattedTopic()}
          onChange={(newTopic) => onChange(newTopic, 'topic')}
          placeholder={intl.formatMessage(messages.topicDropdownEmpty)}
          onCreateTopic={handleTopicCreation}
        />
        <Form.Control.Feedback>
          {intl.formatMessage(messages.topicDropdownHelpText)}
        </Form.Control.Feedback>
      </Form.Group>
      {/* ========== END: MODIFIED TOPIC DROPDOWN ========== */}
    </section>
  );
};

DetailsSection.defaultProps = {
  language: '',
  topic: '',
};

DetailsSection.propTypes = {
  language: PropTypes.string,
  languageOptions: PropTypes.arrayOf(
    PropTypes.arrayOf(PropTypes.string.isRequired).isRequired,
  ).isRequired,
  topic: PropTypes.string,
  topicOptions: PropTypes.arrayOf(
    PropTypes.string.isRequired,
  ).isRequired,
  onChange: PropTypes.func.isRequired,
};

export default DetailsSection;