// @ts-ignore
import { Request, Response } from 'express';

export default {
  'POST /api/v1/component_change/:name/recover': (req: Request, res: Response) => {
    res.status(200).send({
      code: 72,
      data: {
        total: 62,
        items: [
          {
            name: '石娟',
            old_value: '常打化管还利历过想大受期车织音严团。',
            new_value: '政王命合年论容南家选期四除又。',
          },
          {
            name: '陈洋',
            old_value: '存色着发身各平眼者习高应物算。',
            new_value: '带际例主那动铁门万见向王书对。',
          },
          {
            name: '方强',
            old_value: '了是色办经运质形美支身消几感了上万。',
            new_value: '门象议你候员才变住集革因国极中种月。',
          },
          {
            name: '毛超',
            old_value: '活工都市品易花划整性周知反身给光。',
            new_value: '作还价在任整第属与张制局半。',
          },
          {
            name: '范超',
            old_value: '定究需况且红术验眼和验离革消压四。',
            new_value: '心马我适对月效定根务素县志海造。',
          },
          {
            name: '蔡勇',
            old_value: '运把管到题始火声算元加火效书技节还。',
            new_value: '力交集支根也收国系想林理路决前里才。',
          },
          {
            name: '贾娟',
            old_value: '到油点权那少只候有员况备代。',
            new_value: '出接素况四动格青入家做一就儿周石。',
          },
          {
            name: '夏静',
            old_value: '主些必局数口务度流只基向连有。',
            new_value: '外素许花听色具验如调工五亲化世。',
          },
          {
            name: '赵平',
            old_value: '细品转易化正山示观离基治人响温备争。',
            new_value: '务众联反层商京究查般管计农品统。',
          },
          {
            name: '贺平',
            old_value: '消些思除以样片劳知传日见。',
            new_value: '连作行日前最亲地例术华般共越时度。',
          },
          {
            name: '苏平',
            old_value: '格政证想回美眼称济华都气支处明收。',
            new_value: '组张照场三即基度专土现想。',
          },
          {
            name: '曹伟',
            old_value: '头近两何都带信其成前二然地千标海。',
            new_value: '于解指九龙用进华各来件几。',
          },
        ],
      },
      msg: '石节车面命需因但结快义适它百历放。',
      success: true,
    });
  },
};
