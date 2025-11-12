module.exports = {
  multipass: true,
  plugins: [
    {
      // Include and override the built-in plugins
      name: "preset-default",
      params: {
        overrides: {
          removeViewBox: false,
          // prevent breaking scaling for SVGs that are scaled with HTML, CSS or JS
          // see: https://github.com/svg/svgo/issues/1128
          removeTitle: false,
          removeDesc: false,
          // not necessary for safety, but better for accessibility
        },
      },
    },
    {
      // Better for accessibility
      name: "removeUnknownsAndDefaults",
      params: {
        keepRoleAttr: true,
      },
    },

    "prefixIds",
    // prevents conflicts with inline SVGs on the same page by prefixing with the name of the file
    // see: https://github.com/svg/svgo/issues/674
  ],
};
