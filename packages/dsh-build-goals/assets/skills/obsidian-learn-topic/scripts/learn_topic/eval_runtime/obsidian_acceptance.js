/* Returns semantic observation data; the caller decides whether mutation is authorized. */
module.exports = function collectLearnTopicObservation(app, roadmapRoot) {
  const files = app.vault.getMarkdownFiles().filter((file) => file.path.startsWith(`${roadmapRoot}/`));
  return {
    schema_version: 1,
    roadmap_root: roadmapRoot,
    markdown_count: files.length,
    paths: files.map((file) => file.path).sort(),
  };
};
