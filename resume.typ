// --- Jinja2 Data Placeholders ---
#let name = "{{ name }}"
#let contact_data = {{ contact }} // Renamed to avoid conflict if 'contact' is a Typst keyword/function
#let skills_list = {{ skills }}     // Renamed for clarity
#let experience_list = {{ experience }}
#let projects_list = {{ projects }}
#let education_list = {{ education }}
#let references_list = {{ references }}

// --- Document Setup ---
#set document(author: name, title: name + " Resume")
#set page(
  paper: "a4",
  margin: (left: 1.5cm, right: 1.5cm, top: 2cm, bottom: 2cm)
)
#set text(font: "New Computer Modern", lang: "en", size: 10.5pt) // Changed font to New Computer Modern

// --- Helper Functions & Styles ---

// Section Title Style
#let section_title(title_content) = {
  v(1em) // Space before section title
  text(weight: "bold", size: 14pt)[#title_content]
  line(length: 100%, stroke: 0.4pt) // Underline
  v(0.6em) // Space after title
}

// Bullet point item
#let bullet_item(content) = {
  grid(
    columns: (auto, 1fr),
    gutter: 0.5em,
    text(size: 11pt)[•], // Bullet symbol
    content
  )
  v(0.3em)
}

// --- Resume Content ---

// Name (Centered, Large)
#align(center)[
  #text(size: 22pt, weight: 700)[#name]
]
#v(0.5em) // Vertical space after name

// Contact Information (Centered)
#let show_styled_contact(data) = {
  let items = ()
  if data.email != none { items.push(text(size: 9pt)[#data.email]) }
  if data.phone != none { items.push(text(size: 9pt)[#data.phone]) }
  if data.linkedin != none { items.push(text(size: 9pt)[#link("https://" + data.linkedin.replace("https://", ""))[#data.linkedin]]) }
  if data.github != none { items.push(text(size: 9pt)[#link("https://" + data.github.replace("https://", ""))[#data.github]]) }

  if items.len() > 0 {
    align(center)[
      #items.join("  ·  ") // Join with a separator
    ]
    v(1.2em) // Space after contact block
  }
}
#show_styled_contact(contact_data)

// --- Sections ---

// Skills Section
#if skills_list.len() > 0 {
  section_title("Skills")
  for skill_item in skills_list {
    text(weight: "semibold")[#skill_item.skill_name]
    v(0.2em)
    for point in skill_item.bullet_points {
      bullet_item(point)
    }
    v(0.5em) // Space after each skill entry
  }
}

// Experience Section
#if experience_list.len() > 0 {
  section_title("Experience")
  for exp_item in experience_list {
    text(weight: "semibold")[#exp_item.experience_name]
    if exp_item.years != none {
      text(size: 9pt)[ (#exp_item.years)]
    }
    v(0.2em)
    for point in exp_item.bullet_points {
      bullet_item(point)
    }
    v(0.5em) // Space after each experience entry
  }
}

// Projects Section
#if projects_list.len() > 0 {
  section_title("Projects")
  for proj_item in projects_list {
    text(weight: "semibold")[#proj_item.project_name]
    if proj_item.github_link != none {
      text(size: 9pt)[ (#link("https://" + proj_item.github_link.replace("https://", ""))[#proj_item.github_link])]
    }
    v(0.2em)
    for point in proj_item.bullet_points {
      bullet_item(point)
    }
    v(0.5em) // Space after each project entry
  }
}

// Education Section
#if education_list.len() > 0 {
  section_title("Education")
  for edu_item in education_list {
    text(weight: "semibold")[#edu_item.education_name, #edu_item.institution]
    let details_content = [] // Initialize as empty content
    if edu_item.start != none {
      details_content = details_content + edu_item.start + " - " + (if edu_item.end != none { edu_item.end } else { "Present" })
    }
    if edu_item.grade != none {
      if details_content != [] { // If there's already start/end date info, add a comma separator
        details_content = details_content + ", "
      }
      details_content = details_content + "Grade: " + edu_item.grade
    }
    if details_content != [] { // Check if any content was actually added
      text(size: 9pt)[ (#details_content)]
    }
    v(0.5em) // Space after each education entry
  }
}

// References Section
#if references_list.len() > 0 {
  section_title("References")
  for ref_item in references_list {
    text(weight: "semibold")[#ref_item.referer_name, #ref_item.referer_institute]
    let details_content = [] // Initialize as empty content
    if ref_item.position != none {
      details_content = details_content + ref_item.position
    }
    if ref_item.connection_type != none {
      if details_content != [] { // If there's already position info, add a comma separator
        details_content = details_content + ", "
      }
      details_content = details_content + ref_item.connection_type
    }
    if ref_item.institution_url != none {
      if details_content != [] { // If there's already other info, add a space separator
        details_content = details_content + " "
      }
      details_content = details_content + text(size: 9pt)[(#link("https://" + ref_item.institution_url.replace("https://", ""))[#ref_item.institution_url])]
    }

    if details_content != [] { // Check if any content was actually added
      text(size: 9pt)[ (#details_content)]
    }
    v(0.5em) // Space after each reference entry
  }
}
