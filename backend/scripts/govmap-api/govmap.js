const puppeteer = require('puppeteer');
const fs = require('fs');

const file = fs.readFileSync('n_tel_aviv.json', 'utf8');
const data = JSON.parse(file);
const proj4Content = fs.readFileSync('proj4-src.js', 'utf8'); 
const findClosestHood = (arr) => {
  if (!arr || arr.length === 0) {
    return null;
  }

  return arr.reduce((closest, current) => {
    return current.distance < closest.distance ? current : closest;
  }, arr[0]);
};
const delay = (ms) =>{
  return new Promise(resolve => setTimeout(resolve, ms));
}


(async () => {
  debugger;
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.goto('about:blank');
  await page.addScriptTag({ url: 'https://code.jquery.com/jquery-1.12.1.min.js' });
  await page.addScriptTag({ url: 'https://www.govmap.gov.il/govmap/api/govmap.api.js' });
  await page.addScriptTag({ content: proj4Content }); 
  await page.addScriptTag({ content: `const findClosestHood = ${findClosestHood.toString()}` });
  await page.addScriptTag({ content: `const delay = ${delay.toString()}` });

  await page.evaluate(() => {
    proj4.defs("ITM", "+proj=tmerc +lat_0=31.73439361111111 +lon_0=35.20451694444445 +k=1.0000067 +x_0=219529.584 +y_0=626907.39 +ellps=GRS80 +towgs84=-48,55,52,0,0,0,0 +units=m +no_defs");
  });

  const results = await page.evaluate(async (data) => {
    const allResults = [];

    for (let item of data) {
      await delay(500);
      const [longitude, latitude] = item['center'];
      try {
        const [itmX, itmY] = proj4('EPSG:4326', 'ITM', [longitude, latitude]);

        const params = {
          LayerName: 'Neighborhood',
          Point: { x: itmX, y: itmY },
          Radius: 1000
        };

        const response = await govmap.getLayerData(params);
        console.log(response);
        const closest = findClosestHood(response.data);
        allResults.push({
          ...item,
          neigborhood_name: closest['Fields'][0]['Value'],
          city_name: closest['Fields'][1]['Value']
        });
      } catch (error) {
        console.error("error:", error);
      }
    }

    return allResults;
  }, data);

  fs.writeFileSync('govmapData.json', JSON.stringify(results, null, 2));

  await browser.close();
  console.log("all done");
})();