// --- Jinja2 Data Placeholders ---
#let name = "{{ name }}"
#let contact_data = {{ contact }}
#let summary_text = {{ summary }}
#let image_path_val = {{ image_path }}
#let skills_list = {{ skills }}
#let experience_list = {{ experience }}
#let projects_list = {{ projects }}
#let education_list = {{ education }}
#let references_list = {{ references }}

// --- Document Setup ---
#set document(author: name, title: name + " Resume")
#set page(
  paper: "a4",
  margin: (left: 1cm, right: 1cm, top: 1cm, bottom: 1cm)
)
#set text(font: "New Computer Modern", lang: "en", size: 10.75pt)

// --- Iconography (Placeholder for now, assuming you'll provide SVGs or similar) ---
#let icon_email = "✉" // Placeholder
#let icon_phone = "📞" // Placeholder
#let icon_linkedin = "🔗" // Placeholder - Consider using a proper LinkedIn icon
#let icon_github = "🐙"  // Placeholder - Consider using a proper GitHub icon
#let icon_website = "🌐" // Placeholder
#let element_title = "▶︎▶︎"
#let grade = "Grade:"
#let string_space = "   "
#let at = "at"

// --- Helper Functions & Styles ---

// Section Title Style
#let section_title(title_content) = {
  v(0.0em) // Space before section title
  text(weight: "bold", size: 14pt)[#title_content]
  line(length: 100%, stroke: 0.4pt) // Underline
  v(0.0em) // Space after title
}

// Bullet point item
#let bullet_item(content) = {
  grid(
    columns: (auto, 1fr),
    gutter: 0.5em,
    text(size: 9pt)[•], // Bullet symbol
    content
  )
  v(0.0em)
}

// --- Resume Content ---

// Header with Image, Name & Contact Information
#if image_path_val != none and image_path_val != "" {
  // Layout with image on left and name/contact on right
  grid(
    columns: (3.5cm, 1fr), // Image column width, remaining space for text
    gutter: 0.6cm, // Space between image and text
    // Left column: Image
    align(top)[
      #image(image_path_val, width: 3.5cm)
    ],
    // Right column: Name and Contact
    align(top)[
      // Name
      #text(size: 12pt, weight: "semibold")[#name]
      #v(0.0em)
      
      // Contact Information
      #let show_styled_contact(data) = {
        let items = ()
        if data.email != none { items.push(text(size: 9pt)[#icon_email #data.email]) }
        if data.phone != none { items.push(text(size: 9pt)[#icon_phone #data.phone]) }
        if data.linkedin != none { items.push(text(size: 9pt)[#icon_linkedin #link("https://" + data.linkedin.replace("https://", ""))[#data.linkedin]]) }
        if data.github != none { items.push(text(size: 9pt)[#icon_github #link("https://" + data.github.replace("https://", ""))[#data.github]]) }
        if data.website != none { items.push(text(size: 9pt)[#icon_website #link("https://" + data.website.replace("https://", ""))[#data.website]]) }

        if items.len() > 0 {
          // Stack contact items vertically for better use of space
          for item in items {
            item
            v(0.0em)
          }
        }
      }
      #show_styled_contact(contact_data)
    ]
  )
  v(0.0em) // Space after header
} else {
  // No image - centered layout as before
  align(center)[
    #text(size: 16pt, weight: 700)[#name]
  ]
  v(0.0em)
  
  // Contact Information (Centered)
  let show_styled_contact(data) = {
    let items = ()
    if data.email != none { items.push(text(size: 9pt)[#icon_email #data.email]) }
    if data.phone != none { items.push(text(size: 9pt)[#icon_phone #data.phone]) }
    if data.linkedin != none { items.push(text(size: 9pt)[#icon_linkedin #link("https://" + data.linkedin.replace("https://", ""))[#data.linkedin]]) }
    if data.github != none { items.push(text(size: 9pt)[#icon_github #link("https://" + data.github.replace("https://", ""))[#data.github]]) }
    if data.website != none { items.push(text(size: 9pt)[#icon_website #link("https://" + data.website.replace("https://", ""))[#data.website]]) }

    if items.len() > 0 {
      align(center)[
        #items.join("  ·  ") // Join with a separator
      ]
      v(0.0em) // Space after contact block
    }
  }
  show_styled_contact(contact_data)
}

// Summary Section
#if summary_text != none and summary_text != "" {
  section_title("Summary")
  text(summary_text)
  v(0.0em)
}

// Skills Section
#if skills_list.len() > 0 {
  section_title("Skills")
  grid(
    columns: (1fr, 1fr), // Two equal columns
    gutter: 0.4cm,      // Space between columns
    ..skills_list.map(skill_item => block[ // Use .map to transform each skill into a block
      #text(size:11pt, weight: "bold")[#element_title #skill_item.skill_name]
      #v(0.0em)
      #for point in skill_item.bullet_points {
        bullet_item(point)
      }
      #v(0.0em) // Space after each skill entry
    ])
  )
}

// Experience Section
#if experience_list.len() > 0 {
  section_title("Experience")
  for exp_item in experience_list {
    text(weight: "semibold")[#element_title #exp_item.experience_name]
    if exp_item.years != none {
      text(size: 9pt)[ (#exp_item.years)]
    }
    v(0.0em)
    for point in exp_item.bullet_points {
      bullet_item(point)
    }
    v(0.0em) // Space after each experience entry
  }
}

// Projects Section
#if projects_list.len() > 0 {
  section_title("Projects")
  for proj_item in projects_list {
    text(weight: "semibold", size:12pt)[#element_title #proj_item.project_name]
    if proj_item.github_link != none {
      text(size: 9pt)[ (#link("https://" + proj_item.github_link.replace("https://", ""))[#proj_item.github_link])]
    }
    v(0.0em)
    for point in proj_item.bullet_points {
      bullet_item(point)
    }
    v(0.0em) // Space after each project entry
  }
}

// Education Section
#if education_list.len() > 0 {
  section_title("Education")
  for edu_item in education_list {
    text(weight: "semibold", size:12pt)[#element_title #edu_item.education_name]
    v(0.0em)
    text(weight: 550)[#string_space #edu_item.institution]
    let details_content = [] // Initialize as empty content
    if edu_item.start != none {
      details_content = details_content + edu_item.start + " - " + (if edu_item.end != none { edu_item.end } else { "Present" })
    }
    if details_content != [] { // Check if any content was actually added
      text(size: 9pt)[ (#details_content)]
    }
    v(0.0em) // Space after each education entry
    text()[#string_space #grade #edu_item.grade]
    v(0.0em)
  }
}

// References Section
#if references_list.len() > 0 {
  section_title("References")
  for ref_item in references_list {
    text(weight: "semibold")[#ref_item.referer_name]
    v(0.0em)
    text(weight: 550)[#ref_item.position at #ref_item.referer_institute]
    text()[(#ref_item.institution_url)]
    v(0.0em)
    text(weight: 550)[Connection: #ref_item.connection_type]
  }
}