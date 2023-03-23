// @ts-ignore
import { Request, Response } from 'express';

export default {
  'POST /api/v1/deployments/:name/recover': (req: Request, res: Response) => {
    res.status(200).send({
      code: 62,
      data: {
        total: 98,
        items: [
          {
            name: '邹强',
            old_value: '那号道统作象历极选于采开指织。',
            new_value: '算天际次酸情代格原经产也那九参当复。',
          },
          {
            name: '萧磊',
            old_value: '回全程社该须军线属化素全场议水。',
            new_value: '容斯九争院变眼知和族现则每空被。',
          },
          {
            name: '叶平',
            old_value: '还天又体车当好细下儿太生反真西几。',
            new_value: '两第得除容学者以比数运程干两山。',
          },
          {
            name: '余超',
            old_value: '今基眼才之深部们较意号备术高真院。',
            new_value: '极当类战而科科则六马从得越具步。',
          },
          {
            name: '沈芳',
            old_value: '属思正非先信识流性真为消证没。',
            new_value: '且那细事极包事解角接目那记京。',
          },
          {
            name: '田平',
            old_value: '争严进确维打系拉记去矿儿社动事西阶。',
            new_value: '人适去商有素内应今北电内山导状动华领。',
          },
        ],
      },
      msg: '导习片住又管性很观克目从这。',
      success: false,
    });
  },
};
