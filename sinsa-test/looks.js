// Two crayon boxes for the side-by-side style frame: the base style (crayon-book) and Crayon Case.
// The scene code is the same; only these values differ.
export const LOOKS = {
  base: {
    paper: [0.957, 0.937, 0.890],          // #f4efe3
    age: 0, edge: 0, vig: 0.32,
    ink: '#2d3263',                        // outlines (indigo, never black)
    wall: '#e7b867', roof: '#d4483c', wood: '#7a4b31', grass: '#62a24c', leaf: '#62a24c',
    sky: '#79acd9', coat: '#d4483c', skin: '#f4c7a4', hair: '#7a4b31', sun: '#f5c63c',
    winLit: '#f5c63c', clue: '#ee8ea4', shoe: '#2d3263',
    wax: '#fbfaf4',                        // white wax for resist
    wash: [0.15, 0.19, 0.44],              // ultramarine
    face: 'cute', ghost: 0, boil: 1,
    title: { font: 'Gaegu', weight: 700, size: 74 },
  },
  case: {
    paper: [0.863, 0.800, 0.659],          // #dccca8 yellowed, stained paper
    age: 1, edge: 0.85, vig: 0.42,
    ink: '#2d3263',                        // outlines stay indigo, as in the base
    wall: '#8a7d6b',                       // grey-brown
    roof: '#5a4636',                       // umber
    wood: '#4e4037',
    grass: '#77755c', leaf: '#6a6a55',     // olive-grey
    sky: '#7d8c9b',                        // faded blue
    coat: '#5f7186',                       // faded blue
    skin: '#c9bba3',                       // ash, light pressure
    hair: '#3b3936',                       // ink grey (먹색)
    sun: '#bfb59f',                        // a sun with no warmth left
    winLit: '#7d8c9b',                     // faded blue: nobody home
    clue: '#FF1493',                       // THE accent: hot pink, only on what matters
    shoe: '#3b3936',
    wax: null,                             // clear candle wax = paper colour (invisible until the stain passes)
    wash: [0.62, 0.52, 0.36],              // dirty water / tea stain
    blood: [1.0, 0.078, 0.576],            // #FF1493: blood is the accent too, as a covering stain
    face: 'blank', ghost: 1, boil: 0.5,
    title: { font: 'Freesentation', weight: 600, size: 66 },
  },
};
