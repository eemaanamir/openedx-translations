function toggleElementClass(element, class_name = "hidden") {
  if (element.classList.contains(class_name)) {
    element.classList.remove(class_name);
  } else {
    element.classList.add(class_name);
  }
}

function prerequisitsHandler() {
  var all_courses_elements = document.querySelectorAll(".all-courses");
  var follow_up_courses_elements = document.querySelectorAll(".follow-up-courses");
  all_courses_elements.forEach((element) => {
    toggleElementClass(element);
  });
  follow_up_courses_elements.forEach((element) => {
    toggleElementClass(element);
  });

  // toggle button text
  var prerequisite_btn = document.getElementById("study-next-btn");
  const class_name = "showing-follow-courses";

  if (prerequisite_btn.classList.contains(class_name)) {
    prerequisite_btn.innerText = gettext("What to study next?");
    prerequisite_btn.classList.remove(class_name);
  } else {
    prerequisite_btn.innerText = gettext("Show All Courses");
    prerequisite_btn.classList.add(class_name);
  }
}


/**
 * Filter facet options based on search input
 */
function filterFacetOptions(searchInput) {
  
  const searchTerm = searchInput.value.toLowerCase().trim();
  const facetContainer = searchInput.closest('.facet-container');
  
  if (!facetContainer) {
    return;
  }
  
  const facetList = facetContainer.querySelector('.facet-list');
  
  if (!facetList) {
    return;
  }
  
  const facetOptions = facetList.querySelectorAll('li');
  let visibleCount = 0;
  
  facetOptions.forEach((option) => {
    const facetOption = option.querySelector('.facet-option');
    const optionText = facetOption ? facetOption.textContent.trim().toLowerCase() : '';
    
    // Check if the search term matches the option text
    if (searchTerm === '' || optionText.includes(searchTerm)) {
      option.style.display = '';
      visibleCount++;
    } else {
      option.style.display = 'none';
    }
  });
  
  
  // Show/hide a "no results" message if needed
  let noResultsMsg = facetContainer.querySelector('.facet-no-results');
  if (visibleCount === 0 && searchTerm !== '') {
    if (!noResultsMsg) {
      noResultsMsg = document.createElement('li');
      noResultsMsg.className = 'facet-no-results';
      noResultsMsg.style.padding = '10px';
      noResultsMsg.style.color = '#6c7885';
      noResultsMsg.style.fontSize = '14px';
      noResultsMsg.textContent = typeof gettext !== 'undefined' ? gettext('No results found') : 'No results found';
      facetList.appendChild(noResultsMsg);
    }
    noResultsMsg.style.display = '';
  } else if (noResultsMsg) {
    noResultsMsg.style.display = 'none';
  }
}

// Use event delegation on document with keyup
document.addEventListener('keyup', function(e) {
  // Check if the target is a facet search input
  if (e.target && e.target.classList.contains('lng-srch-facet-input')) {
    filterFacetOptions(e.target);
  }
});

// Also handle input event for immediate response (paste, autocomplete, etc.)
document.addEventListener('input', function(e) {
  if (e.target && e.target.classList.contains('lng-srch-facet-input')) {
    filterFacetOptions(e.target);
  }
});

// Handle escape key to clear search
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape' && e.target && e.target.classList.contains('lng-srch-facet-input')) {
    e.target.value = '';
    filterFacetOptions(e.target);
    e.target.blur();
  }
});

