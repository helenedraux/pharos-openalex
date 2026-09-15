import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';
const [input, output, previews] = process.argv.slice(2);
const data = JSON.parse(await fs.readFile(input, 'utf8'));
const workbook = Workbook.create();
const safe = value => typeof value === 'string' && /^[=+@\-\t\r]/.test(value) ? "'" + value : value;
function sheet(name, title, headers, rows, widths) {
  const s = workbook.worksheets.add(name);
  s.showGridLines = false;
  s.getRange('A2').values = [[title]];
  s.getRange('A2').format.font = { name:'Arial', size:14, bold:true, color:'#183047' };
  const matrix = [headers, ...rows].map(row => row.map(safe));
  const area = s.getRangeByIndexes(4,0,matrix.length,headers.length);
  area.values = matrix;
  area.format.font = { name:'Arial', size:10, color:'#183047' };
  area.format.rowHeight = 28;
  area.format.verticalAlignment = 'top';
  area.format.wrapText = true;
  widths.forEach((width,i) => s.getRangeByIndexes(0,i,matrix.length+4,1).format.columnWidth = width);
  const header = s.getRangeByIndexes(4,0,1,headers.length);
  header.format.fill = '#183047';
  header.format.font = { name:'Arial', size:10, color:'#FFFFFF', bold:true };
  header.format.rowHeight = 32;
  if (rows.length) {
    const table=s.tables.add(`A5:${String.fromCharCode(64+headers.length)}${rows.length+5}`,true,name.replace(/ /g,'')+'Table');
    table.style='TableStyleLight1';
  }
  s.freezePanes.freezeRows(5);
  return s;
}
const context=sheet('Report','Pharos coverage overview',['Field','Saved value'],[...data.metadata,...data.warnings.map(w=>['Limitation',w])],[29,110]);
context.getRange(`A6:B${data.metadata.length+data.warnings.length+5}`).format.rowHeight=42;
data.metadata.forEach(([label,value],i)=>{
  const cell=context.getRangeByIndexes(i+5,1,1,1);
  if(['Period from','Period through','Overview retrieved','Source-view retrieved'].includes(label)) {
    cell.values=[[new Date(value)]];
    cell.setNumberFormat(label.startsWith('Period')?'yyyy-mm-dd':'yyyy-mm-dd hh:mm:ss "UTC"');
  } else if(typeof value==='number') cell.setNumberFormat('#,##0');
});
const measures=sheet('Measures','Counts and denominators',data.headers,data.rows,[28,68,15,16,13,27,50,100]);
measures.getRange(`C6:D${data.rows.length+5}`).setNumberFormat('#,##0');
measures.getRange(`E6:E${data.rows.length+5}`).setNumberFormat('0.00%');
data.rows.forEach((r,i)=>{
  measures.getRangeByIndexes(i+5,4,1,1).formulas=[[`=IF(D${i+6}=0,"Unknown",C${i+6}/D${i+6})`]];
  measures.getRangeByIndexes(i+5,0,1,8).format.rowHeight=Math.max(34,Math.ceil(String(r[1]).length/58)*14+12,Math.ceil(String(r[7]).length/90)*14+12);
});
const affiliations=sheet('Sample works','Work links behind the raw affiliation sample',['Raw affiliation','OpenAlex work ID','Work title','Year'],data.affiliation_works,[85,48,90,12]);
data.affiliation_works.forEach((r,i)=>affiliations.getRangeByIndexes(i+5,0,1,4).format.rowHeight=Math.max(42,Math.ceil(String(r[0]).length/75)*14+12,Math.ceil(String(r[2]).length/80)*14+12));
const provenance=sheet('Queries','OpenAlex query provenance',['Retrieved at','Query URL','Response SHA-256'],data.queries,[30,110,75]);
provenance.getRange(`A6:C${data.queries.length+5}`).format.rowHeight=66;
data.queries.forEach((row,i)=>{
  const cell=provenance.getRangeByIndexes(i+5,0,1,1);
  cell.values=[[new Date(row[0])]];
  cell.setNumberFormat('yyyy-mm-dd hh:mm:ss "UTC"');
});
workbook.recalculate();
const check=await workbook.inspect({kind:'table',range:'Measures!A5:F12',include:'values,formulas',tableMaxRows:8,tableMaxCols:6,maxChars:1500});
const errors=await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:1500});
if(previews){
  await fs.mkdir(previews,{recursive:true});
  await fs.writeFile(`${previews}/verification.txt`,check.ndjson+'\n'+errors.ndjson);
  for(const [name,range] of [['Report','A1:B17'],['Measures','A1:F15'],['Sample works','A1:D10'],['Queries','A1:C9']]){
    const png=await workbook.render({sheetName:name,range,scale:1.5,format:'png'});
    await fs.writeFile(`${previews}/${name.replace(/ /g,'-')}.png`,new Uint8Array(await png.arrayBuffer()));
  }
}
await (await SpreadsheetFile.exportXlsx(workbook)).save(output);
