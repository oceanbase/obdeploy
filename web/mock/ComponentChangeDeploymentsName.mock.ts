// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/component_change/deployment': (req: Request, res: Response) => {
    res.status(200).send({
      code: 78,
      data: {
        total: 76,
        items: [
          {
            name: '吕洋',
            ob_version: '4.2.3',
            create_date: '2024年7月',
            deploy_user: 'root'
          },
        ],
      },
      msg: '级表真养取六色前音将个制情近战度照。',
      success: true,
    });
  },
};
