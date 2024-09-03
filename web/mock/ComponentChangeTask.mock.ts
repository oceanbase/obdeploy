// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/component_change/:name/component_change': (req: Request, res: Response) => {
    res.status(200).send({
      code: 94,
      data: {
        total: 67,
        finished: 99,
        current: '起此求统根属十级三了进太厂华果。',
        status: {
          '0': 'S',
          '1': 'U',
          '2': 'C',
          '3': 'C',
          '4': 'E',
          '5': 'S',
          '6': 'S',
          '7': 'F',
          '8': 'U',
          '9': 'L',
        },
        msg: '认车准都却去题计是年一果热支选步清。',
        info: [
          {
            component: '素文记然百积青需无式原标整一。',
            status: { '0': 'P', '1': 'E', '2': 'N', '3': 'D', '4': 'I', '5': 'N', '6': 'G' },
            result: {
              '0': 'S',
              '1': 'U',
              '2': 'C',
              '3': 'C',
              '4': 'E',
              '5': 'S',
              '6': 'S',
              '7': 'F',
              '8': 'U',
              '9': 'L',
            },
          },
          {
            component: '切起着八压在治王派连九生层。',
            status: { '0': 'P', '1': 'E', '2': 'N', '3': 'D', '4': 'I', '5': 'N', '6': 'G' },
            result: {
              '0': 'S',
              '1': 'U',
              '2': 'C',
              '3': 'C',
              '4': 'E',
              '5': 'S',
              '6': 'S',
              '7': 'F',
              '8': 'U',
              '9': 'L',
            },
          },
        ],
      },
      msg: '也气果因住按车才层给八习较场南见查离。',
      success: true,
    });
  },
  'GET /api/v1/component_change/:name/del_component': (req: Request, res: Response) => {
    res
      .status(200)
      .send({ code: 66, data: null, msg: '完住片所各领重江京家按般感增气。', success: false });
  },
};
